"""
Notification queue management with rate limiting
"""
import asyncio
import uuid
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from app.models import (
    QueuedNotification,
    NotificationChannel,
    NotificationStatus,
    NotificationPriority,
)
from app.config import settings

logger = logging.getLogger(__name__)


class NotificationQueue:
    """
    Thread-safe notification queue with rate limiting per channel
    """

    def __init__(self):
        self.queues: Dict[NotificationChannel, deque] = {
            channel: deque() for channel in NotificationChannel
        }
        self.notifications: Dict[str, QueuedNotification] = {}
        self.sent_history: List[QueuedNotification] = []
        self.rate_trackers: Dict[NotificationChannel, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def enqueue(
        self,
        channel: NotificationChannel,
        recipient: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> str:
        """
        Add a notification to the queue

        Args:
            channel: Notification channel
            recipient: Recipient identifier
            message: Message content
            priority: Message priority

        Returns:
            message_id: Unique message identifier

        Raises:
            ValueError: If queue is full
        """
        async with self._lock:
            # Check queue size
            total_queued = sum(len(q) for q in self.queues.values())
            if total_queued >= settings.MAX_QUEUE_SIZE:
                raise ValueError("Queue is full")

            # Create notification
            message_id = str(uuid.uuid4())
            notification = QueuedNotification(
                message_id=message_id,
                channel=channel,
                recipient=recipient,
                message=message,
                priority=priority,
                status=NotificationStatus.QUEUED,
                created_at=datetime.utcnow(),
            )

            # Add to queue (priority items go to front)
            if priority == NotificationPriority.URGENT:
                self.queues[channel].appendleft(notification)
            else:
                self.queues[channel].append(notification)

            self.notifications[message_id] = notification
            logger.info(f"Enqueued notification {message_id} to {channel.value}")

            return message_id

    async def dequeue(
        self, channel: NotificationChannel
    ) -> Optional[QueuedNotification]:
        """
        Get the next notification from queue if not rate limited

        Args:
            channel: Channel to dequeue from

        Returns:
            Notification or None if rate limited or queue empty
        """
        async with self._lock:
            # Check if we have messages
            if not self.queues[channel]:
                return None

            # Check rate limit
            if not self._can_send(channel):
                logger.debug(f"Rate limited on {channel.value}")
                return None

            # Get next notification
            notification = self.queues[channel].popleft()
            notification.status = NotificationStatus.SENDING

            # Track for rate limiting
            self._track_send(channel)

            return notification

    async def mark_sent(self, message_id: str) -> None:
        """Mark a notification as successfully sent"""
        async with self._lock:
            if message_id in self.notifications:
                notification = self.notifications[message_id]
                notification.status = NotificationStatus.SENT
                self.sent_history.append(notification)
                logger.info(f"Notification {message_id} sent successfully")

    async def mark_failed(
        self, message_id: str, error: str, should_retry: bool = True
    ) -> None:
        """
        Mark a notification as failed and optionally retry

        Args:
            message_id: Notification ID
            error: Error message
            should_retry: Whether to retry sending
        """
        async with self._lock:
            if message_id not in self.notifications:
                return

            notification = self.notifications[message_id]
            notification.last_error = error
            notification.retry_count += 1

            # Determine retry limits based on channel
            max_retries = (
                settings.TELEGRAM_RETRY_COUNT
                if notification.channel == NotificationChannel.TELEGRAM
                else settings.SMS_RETRY_COUNT
            )

            if should_retry and notification.retry_count < max_retries:
                notification.status = NotificationStatus.RETRYING
                # Re-queue for retry
                self.queues[notification.channel].append(notification)
                logger.warning(
                    f"Notification {message_id} failed, retrying "
                    f"({notification.retry_count}/{max_retries}): {error}"
                )
            else:
                notification.status = NotificationStatus.FAILED
                logger.error(
                    f"Notification {message_id} failed permanently: {error}"
                )

    def _can_send(self, channel: NotificationChannel) -> bool:
        """
        Check if we can send on this channel based on rate limits

        Args:
            channel: Channel to check

        Returns:
            True if we can send, False if rate limited
        """
        rate_limit = (
            settings.TELEGRAM_RATE_LIMIT
            if channel == NotificationChannel.TELEGRAM
            else settings.SMS_RATE_LIMIT
        )

        # Clean old entries
        cutoff = datetime.utcnow() - timedelta(
            seconds=settings.RATE_LIMIT_WINDOW_SECONDS
        )
        tracker = self.rate_trackers[channel]
        while tracker and tracker[0] < cutoff:
            tracker.popleft()

        # Check if under limit
        return len(tracker) < rate_limit

    def _track_send(self, channel: NotificationChannel) -> None:
        """Track a send for rate limiting"""
        self.rate_trackers[channel].append(datetime.utcnow())

    async def get_status(self, message_id: str) -> Optional[QueuedNotification]:
        """Get the status of a notification"""
        async with self._lock:
            return self.notifications.get(message_id)

    async def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        async with self._lock:
            return {
                "queued": {
                    channel.value: len(queue)
                    for channel, queue in self.queues.items()
                },
                "total_queued": sum(len(q) for q in self.queues.values()),
                "sent_today": len(
                    [
                        n
                        for n in self.sent_history
                        if n.created_at.date() == datetime.utcnow().date()
                    ]
                ),
                "total_sent": len(self.sent_history),
            }

    async def get_history(
        self, limit: int = 100, offset: int = 0
    ) -> List[QueuedNotification]:
        """Get sent notification history"""
        async with self._lock:
            return self.sent_history[offset : offset + limit]


# Global queue instance
notification_queue = NotificationQueue()
