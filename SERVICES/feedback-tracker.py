#!/usr/bin/env python3
"""
Human Feedback Tracker
Session #2 - Honest Outreach System

Collects, stores, and reports human feedback from all outreach channels.
Enables learning loop: Outreach → Feedback → Learning → Improvement
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

# Database schema
DB_PATH = Path(__file__).parent / "human_feedback.db"


def init_database():
    """Initialize feedback database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            user_type TEXT NOT NULL,
            message TEXT NOT NULL,
            sentiment TEXT,
            signed_up INTEGER DEFAULT 0,
            reason_not_signed_up TEXT,
            follow_up_needed INTEGER DEFAULT 0,
            honesty_reaction TEXT,
            actual_outcome TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_number INTEGER NOT NULL,
            year INTEGER NOT NULL,
            report_data TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_PATH}")


def add_feedback(
    source: str,
    user_type: str,
    message: str,
    sentiment: Optional[str] = None,
    signed_up: bool = False,
    reason_not_signed_up: Optional[str] = None,
    follow_up_needed: bool = False,
    honesty_reaction: Optional[str] = None,
    notes: Optional[str] = None
):
    """Add new feedback entry."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO feedback (
            timestamp, source, user_type, message, sentiment,
            signed_up, reason_not_signed_up, follow_up_needed,
            honesty_reaction, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        source,
        user_type,
        message,
        sentiment,
        1 if signed_up else 0,
        reason_not_signed_up,
        1 if follow_up_needed else 0,
        honesty_reaction,
        notes
    ))

    conn.commit()
    feedback_id = cursor.lastrowid
    conn.close()

    print(f"✅ Feedback #{feedback_id} recorded from {source}")
    return feedback_id


def get_all_feedback(source: Optional[str] = None):
    """Get all feedback, optionally filtered by source."""

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if source:
        cursor.execute("SELECT * FROM feedback WHERE source = ? ORDER BY timestamp DESC", (source,))
    else:
        cursor.execute("SELECT * FROM feedback ORDER BY timestamp DESC")

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def generate_weekly_report():
    """Generate weekly feedback summary."""

    feedback = get_all_feedback()

    # Group by source
    by_source = {}
    for item in feedback:
        source = item['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(item)

    # Calculate stats
    total = len(feedback)
    signups = sum(1 for f in feedback if f['signed_up'])
    positive = sum(1 for f in feedback if f['sentiment'] == 'positive')
    negative = sum(1 for f in feedback if f['sentiment'] == 'negative')
    skeptical = sum(1 for f in feedback if f['sentiment'] == 'skeptical')

    # Honest reactions
    loved_honesty = sum(1 for f in feedback if f.get('honesty_reaction') == 'positive')

    report = f"""
# Weekly Outreach Feedback Report
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Summary Stats

- **Total Interactions:** {total}
- **Signups:** {signups} ({signups/total*100 if total > 0 else 0:.1f}%)
- **Sentiment:**
  - Positive: {positive}
  - Skeptical: {skeptical}
  - Negative: {negative}

- **Honesty Reception:**
  - Loved transparency: {loved_honesty}

## Feedback by Source

"""

    for source, items in by_source.items():
        report += f"\n### {source.title()}\n"
        report += f"- Total: {len(items)}\n"
        report += f"- Signups: {sum(1 for i in items if i['signed_up'])}\n"
        report += "\n**Sample Feedback:**\n"

        for item in items[:3]:  # Top 3 per source
            report += f'- "{item["message"][:100]}..." ({item["sentiment"]})\n'

    # Quotes section
    report += "\n## Notable Quotes (Exact)\n\n"
    report += "**Positive:**\n"
    for item in feedback:
        if item['sentiment'] == 'positive':
            report += f'- "{item["message"]}"\n'

    report += "\n**Critical/Skeptical:**\n"
    for item in feedback:
        if item['sentiment'] in ['skeptical', 'negative']:
            report += f'- "{item["message"]}"\n'

    # Learnings
    report += "\n## Key Learnings\n\n"
    report += "1. [To be filled in manually based on patterns]\n"
    report += "2. [To be filled in manually based on patterns]\n"
    report += "3. [To be filled in manually based on patterns]\n"

    report += "\n## Next Actions\n\n"
    report += "- [ ] Follow up with signup requests\n"
    report += "- [ ] Address common skepticism points\n"
    report += "- [ ] Update messaging based on feedback\n"

    report += f"\n---\n*Generated by Feedback Tracker*\n"

    return report


def save_weekly_report():
    """Save weekly report to file and database."""

    report = generate_weekly_report()

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"weekly_report_{timestamp}.md"

    with open(report_file, 'w') as f:
        f.write(report)

    print(f"📊 Weekly report saved: {report_file}")

    # Save to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    week = datetime.now().isocalendar()[1]
    year = datetime.now().year

    cursor.execute("""
        INSERT INTO weekly_reports (week_number, year, report_data, created_at)
        VALUES (?, ?, ?, ?)
    """, (week, year, report, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return report_file


def main():
    """Main execution with examples."""

    print("🌟 Human Feedback Tracker")
    print("="*70)

    # Initialize
    init_database()

    # Example: Add some feedback
    print("\n📝 Example: Adding feedback...")

    add_feedback(
        source="reddit_fatfire",
        user_type="customer_prospect",
        message="Love the honesty. Most AI startups are just hype.",
        sentiment="positive",
        signed_up=True,
        honesty_reaction="positive",
        notes="Appreciated experimental framing"
    )

    add_feedback(
        source="reddit_fi",
        user_type="customer_prospect",
        message="How do I know the AI actually understands compatibility?",
        sentiment="skeptical",
        signed_up=False,
        reason_not_signed_up="wants proof of concept",
        follow_up_needed=True
    )

    add_feedback(
        source="linkedin",
        user_type="provider_prospect",
        message="Interesting concept. Zero customers is concerning though.",
        sentiment="skeptical",
        signed_up=False,
        reason_not_signed_up="wants traction first"
    )

    # Show all feedback
    print("\n📊 All Feedback:")
    all_feedback = get_all_feedback()
    for f in all_feedback:
        print(f"  [{f['source']}] {f['message'][:60]}... ({f['sentiment']})")

    # Generate report
    print("\n📈 Generating weekly report...")
    report_file = save_weekly_report()

    print(f"\n✅ Done! Report saved to {report_file}")
    print(f"   Database: {DB_PATH}")


if __name__ == "__main__":
    main()
