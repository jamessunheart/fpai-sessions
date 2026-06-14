"""
Background worker for processing notification queue
"""
import asyncio
import logging
from datetime import datetime

from app.queue import notification_queue
from app.channels import TelegramChannel, SMSChannel
from app.models import NotificationChannel
from app.config import settings

logger = logging.getLogger(__name__)


class NotificationWorker:
    """Background worker to process notification queue"""

    def __init__(self):
        self.telegram = TelegramChannel()
        self.sms = SMSChannel()
        self.running = False
        self.task = None

    async def start(self):
        """Start the worker"""
        if self.running:
            logger.warning("Worker already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._process_loop())
        logger.info("Notification worker started")

    async def stop(self):
        """Stop the worker"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Notification worker stopped")

    async def _process_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Process each channel
                await self._process_channel(NotificationChannel.TELEGRAM)
                await self._process_channel(NotificationChannel.SMS)

                # Sleep briefly before next iteration
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _process_channel(self, channel: NotificationChannel):
        """
        Process notifications for a specific channel

        Args:
            channel: Channel to process
        """
        # Get next notification
        notification = await notification_queue.dequeue(channel)
        if not notification:
            return

        # Get the appropriate channel handler
        if channel == NotificationChannel.TELEGRAM:
            handler = self.telegram
        elif channel == NotificationChannel.SMS:
            handler = self.sms
        else:
            logger.error(f"Unknown channel: {channel}")
            await notification_queue.mark_failed(
                notification.message_id, "Unknown channel", should_retry=False
            )
            return

        # Check if configured
        if not handler.is_configured():
            logger.warning(f"{channel.value} not configured, skipping")
            await notification_queue.mark_failed(
                notification.message_id,
                f"{channel.value} not configured",
                should_retry=False,
            )
            return

        # Try to send
        try:
            success = await handler.send(
                notification.recipient, notification.message
            )
            if success:
                await notification_queue.mark_sent(notification.message_id)
            else:
                await notification_queue.mark_failed(
                    notification.message_id, "Send returned False"
                )
        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Failed to send {notification.message_id} via {channel.value}: {error_msg}"
            )
            await notification_queue.mark_failed(notification.message_id, error_msg)

        # Add delay based on channel settings
        if channel == NotificationChannel.TELEGRAM:
            await asyncio.sleep(settings.TELEGRAM_RETRY_DELAY)
        elif channel == NotificationChannel.SMS:
            await asyncio.sleep(settings.SMS_RETRY_DELAY)


# Global worker instance
worker = NotificationWorker()
