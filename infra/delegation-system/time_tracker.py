"""
Simple time tracker to measure how long tasks take
Use this to quantify time savings when you switch to VAs
"""

import json
import datetime
from pathlib import Path


class TimeTracker:
    def __init__(self, log_path="/root/delegation-system/monitoring/time_log.json"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_path.exists():
            self.log_path.write_text(json.dumps([], indent=2))

    def start_task(self, task_name):
        """Start timing a task"""
        logs = json.loads(self.log_path.read_text())

        entry = {
            "task": task_name,
            "started_at": datetime.datetime.now().isoformat(),
            "completed_at": None,
            "duration_minutes": None,
            "who": "you"
        }

        logs.append(entry)
        self.log_path.write_text(json.dumps(logs, indent=2))

        print(f"⏱️  Started: {task_name}")
        print(f"Start time: {entry['started_at']}")

        return len(logs) - 1  # Return index

    def complete_task(self, task_index):
        """Mark task as complete and calculate duration"""
        logs = json.loads(self.log_path.read_text())

        if task_index >= len(logs):
            print("❌ Task index not found")
            return

        task = logs[task_index]

        if task['completed_at']:
            print("⚠️  Task already completed")
            return

        started = datetime.datetime.fromisoformat(task['started_at'])
        completed = datetime.datetime.now()
        duration = (completed - started).total_seconds() / 60

        task['completed_at'] = completed.isoformat()
        task['duration_minutes'] = round(duration, 1)

        logs[task_index] = task
        self.log_path.write_text(json.dumps(logs, indent=2))

        print(f"✅ Completed: {task['task']}")
        print(f"Duration: {task['duration_minutes']} minutes")
        print(f"Value: ${task['duration_minutes'] * 1.67:.2f} (at $100/hour)")

    def get_summary(self):
        """Get summary of all tracked time"""
        logs = json.loads(self.log_path.read_text())

        completed = [t for t in logs if t['completed_at']]

        if not completed:
            print("No completed tasks yet")
            return

        total_minutes = sum(t['duration_minutes'] for t in completed)
        total_value = total_minutes * 1.67  # $100/hour = $1.67/min

        print(f"\n📊 Time Tracking Summary")
        print(f"=" * 50)
        print(f"Tasks completed: {len(completed)}")
        print(f"Total time: {total_minutes:.1f} minutes ({total_minutes/60:.1f} hours)")
        print(f"Value: ${total_value:.2f} (at $100/hour)")
        print(f"\nTask breakdown:")

        for task in completed:
            print(f"  • {task['task']}: {task['duration_minutes']} min (${task['duration_minutes'] * 1.67:.2f})")


if __name__ == "__main__":
    tracker = TimeTracker()

    # Example usage
    print("Time Tracker Ready!")
    print("\nExample usage:")
    print("  from time_tracker import TimeTracker")
    print("  tracker = TimeTracker()")
    print("  idx = tracker.start_task('Setup Stripe account')")
    print("  # ... do the work ...")
    print("  tracker.complete_task(idx)")
    print("  tracker.get_summary()")
