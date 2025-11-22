"""
Proactive Notifier - Finds James and sends notifications

This component:
- Detects when James needs help
- Sends notifications via desktop/terminal/SMS
- Times notifications intelligently
- Prevents notification fatigue
"""

import subprocess
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path


class ProactiveNotifier:
    """Sends intelligent, timely notifications to James"""

    def __init__(self, context_engine):
        self.context_engine = context_engine
        self.last_notification_time = {}
        self.notification_cooldown = 300  # 5 minutes between similar notifications

    def send_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        priority: str = "normal"
    ) -> Dict:
        """
        Send a notification to James

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type (info, suggestion, alert, error)
            priority: Priority (low, normal, high, urgent)

        Returns:
            Result dict with method used and success status
        """

        # Check cooldown
        if self._is_in_cooldown(notification_type):
            return {"sent": False, "reason": "cooldown", "method": None}

        # Choose notification method based on priority
        methods = self._choose_notification_methods(priority)

        result = {"sent": False, "methods_tried": [], "method": None}

        for method in methods:
            try:
                if method == "desktop":
                    success = self._send_desktop_notification(title, message)
                elif method == "terminal":
                    success = self._send_terminal_notification(title, message)
                elif method == "sms":
                    success = self._send_sms_notification(title, message)
                else:
                    success = False

                result["methods_tried"].append(method)

                if success:
                    result["sent"] = True
                    result["method"] = method
                    break

            except Exception as e:
                print(f"Error sending via {method}: {e}")
                continue

        # Update cooldown
        if result["sent"]:
            self.last_notification_time[notification_type] = datetime.now()

            # Log the notification
            self.context_engine.log_activity(
                "notification_sent",
                "companion-claude",
                {
                    "title": title,
                    "message": message,
                    "type": notification_type,
                    "priority": priority,
                    "method": result["method"]
                }
            )

        return result

    def _choose_notification_methods(self, priority: str) -> list:
        """Choose which notification methods to try based on priority"""

        methods = {
            "low": ["terminal"],
            "normal": ["desktop", "terminal"],
            "high": ["desktop", "terminal", "sms"],
            "urgent": ["sms", "desktop", "terminal"]
        }

        return methods.get(priority, ["desktop", "terminal"])

    def _send_desktop_notification(self, title: str, message: str) -> bool:
        """Send macOS desktop notification"""
        try:
            # Use osascript for macOS notifications
            script = f'''
            display notification "{message}" with title "{title}"
            '''

            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True
            )

            return True

        except Exception as e:
            print(f"Desktop notification failed: {e}")
            return False

    def _send_terminal_notification(self, title: str, message: str) -> bool:
        """Send notification to all open terminals"""
        try:
            # Find all terminal sessions
            sessions_dir = Path("/Users/jamessunheart/Development/docs/coordination/sessions/ACTIVE")

            if not sessions_dir.exists():
                return False

            # Write to a notification file that shell integration can pick up
            notif_file = sessions_dir / "companion_notifications.txt"

            with open(notif_file, "a") as f:
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"\n[{timestamp}] 💬 {title}: {message}\n")

            # Also try to send to current terminal via wall (if available)
            try:
                subprocess.run(
                    ["echo", f"💬 {title}: {message}"],
                    check=False
                )
            except:
                pass

            return True

        except Exception as e:
            print(f"Terminal notification failed: {e}")
            return False

    def _send_sms_notification(self, title: str, message: str) -> bool:
        """Send SMS notification (for urgent alerts only)"""
        # Would integrate with Twilio or similar
        # For now, just a placeholder
        print(f"SMS: {title} - {message}")
        return False

    def _is_in_cooldown(self, notification_type: str) -> bool:
        """Check if this notification type is in cooldown"""
        if notification_type not in self.last_notification_time:
            return False

        last_time = self.last_notification_time[notification_type]
        elapsed = (datetime.now() - last_time).total_seconds()

        return elapsed < self.notification_cooldown

    def send_morning_briefing(self):
        """Send morning briefing"""
        context = self.context_engine.get_current_context()

        priorities = context.get("priorities", [])
        system_state = context.get("system_state", {})

        briefing = f"""Good morning, James!

📊 System Status:
   • {system_state.get('services_online', 0)} services online
   • {system_state.get('sessions_active', 0)} sessions active
   • {system_state.get('git_changes', 0)} uncommitted changes

🎯 Top Priority: {priorities[0]['title'] if priorities else 'No priorities set'}

Type 'companion briefing' for full details."""

        return self.send_notification(
            title="Morning Briefing",
            message=briefing,
            notification_type="briefing",
            priority="normal"
        )

    def send_eod_summary(self):
        """Send end-of-day summary"""
        context = self.context_engine.get_current_context()

        wins = context.get("wins_today", [])

        summary = f"""End of day summary:

✅ Wins Today:
{chr(10).join(f'   • {win}' for win in wins) if wins else '   • No wins recorded'}

Type 'companion eod' for full summary."""

        return self.send_notification(
            title="End of Day Summary",
            message=summary,
            notification_type="eod_summary",
            priority="low"
        )

    def send_blocker_alert(self, blocker: Dict):
        """Alert about a detected blocker"""
        message = f"""Blocker detected: {blocker.get('description')}

Would you like help resolving this?"""

        return self.send_notification(
            title="🚨 Blocker Detected",
            message=message,
            notification_type="blocker",
            priority="high"
        )

    def send_suggestion(self, suggestion: Dict):
        """Send a proactive suggestion"""
        return self.send_notification(
            title="💡 Suggestion",
            message=suggestion.get("message"),
            notification_type="suggestion",
            priority=suggestion.get("priority", "normal")
        )

    def get_active_count(self) -> int:
        """Get number of active notifications"""
        return len(self.last_notification_time)

    def clear_cooldowns(self):
        """Clear all notification cooldowns"""
        self.last_notification_time = {}


if __name__ == "__main__":
    # Test the notifier
    from context_engine import ContextEngine

    engine = ContextEngine()
    notifier = ProactiveNotifier(engine)

    # Test notification
    result = notifier.send_notification(
        title="Test Notification",
        message="This is a test from Companion Claude",
        notification_type="test",
        priority="normal"
    )

    print(f"Notification sent: {result}")
