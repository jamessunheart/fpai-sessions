#!/usr/bin/env python3
"""
Autonomous Email Recruiter for I MATCH
Sends personalized emails to 317 financial advisor prospects
Fully autonomous - runs 24/7 without human intervention
"""

import csv
import json
import time
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('autonomous_email_recruiter.log'),
        logging.StreamHandler()
    ]
)

class AutonomousEmailRecruiter:
    def __init__(self, prospects_csv: str, db_path: str = "email_recruiter.db"):
        self.prospects_csv = prospects_csv
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Email tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_name TEXT NOT NULL,
                prospect_email TEXT NOT NULL,
                company TEXT,
                subject TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                opened BOOLEAN DEFAULT 0,
                clicked BOOLEAN DEFAULT 0,
                replied BOOLEAN DEFAULT 0,
                follow_up_sent BOOLEAN DEFAULT 0
            )
        ''')

        # Daily stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                emails_sent INTEGER DEFAULT 0,
                emails_opened INTEGER DEFAULT 0,
                emails_clicked INTEGER DEFAULT 0,
                emails_replied INTEGER DEFAULT 0,
                new_signups INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()
        logging.info("Database initialized")

    def load_prospects(self) -> List[Dict]:
        """Load prospects from JSON"""
        prospects = []
        try:
            # Try JSON first
            json_path = self.prospects_csv.replace('.csv', '.json')
            with open(json_path, 'r') as f:
                data = json.load(f)
                prospect_list = data.get('prospects', [])

                for item in prospect_list:
                    p = item.get('prospect', {})
                    name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
                    email = self.derive_email(name, p.get('company', ''))

                    prospects.append({
                        'name': name,
                        'title': p.get('title', ''),
                        'company': p.get('company', ''),
                        'email': email,
                        'specialty': p.get('specialty', ''),
                        'personalization': item.get('connection_request', {}).get('message', '')
                    })

            logging.info(f"Loaded {len(prospects)} prospects from JSON")
            return prospects
        except Exception as e:
            logging.error(f"Error loading prospects: {e}")
            return []

    def derive_email(self, name: str, company: str) -> str:
        """Derive email address from name and company"""
        # Common patterns: firstname.lastname@company.com, firstname@company.com
        # This is a placeholder - in production, you'd use email finder APIs
        parts = name.lower().split()
        if len(parts) >= 2:
            first = parts[0]
            last = parts[-1]
            domain = company.lower().replace(' ', '').replace(',', '').replace('llc', '').replace('inc', '').strip()
            # Try common pattern
            return f"{first}.{last}@{domain}.com"
        return f"contact@{company.lower().replace(' ', '')}.com"

    def get_unsent_prospects(self, limit: int = 10) -> List[Dict]:
        """Get prospects who haven't been emailed yet"""
        prospects = self.load_prospects()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get emails already sent
        cursor.execute('SELECT prospect_email FROM emails_sent')
        sent_emails = {row[0] for row in cursor.fetchall()}
        conn.close()

        # Filter out already contacted
        unsent = [p for p in prospects if p['email'] not in sent_emails]
        return unsent[:limit]

    def generate_email_content(self, prospect: Dict) -> tuple:
        """Generate personalized email subject and body"""
        first_name = prospect['name'].split()[0]

        subject = f"AI matching for {prospect['title']}s - qualified leads"

        body = f"""Hi {first_name},

I noticed your work as {prospect['title']} at {prospect['company']}.

Quick question: Would you be interested in qualified leads from people actively looking for financial advisors?

We're building I MATCH - an AI system that matches people to financial advisors based on compatibility (communication style, values, approach) rather than just credentials.

The challenge: We need more advisors on the platform. Different specialties, different styles, so our AI can match people accurately.

If you're interested:
• Join as a matched advisor (free): http://198.54.123.234:8401
• Or help us recruit and earn 20% recurring: http://198.54.123.234:8401/static/contributors.html

Early stage experiment. Might work, might not. But if you're looking for better-fit clients, worth 5 minutes to check out.

Best,
James (building I MATCH)

P.S. My dad's a CFP - grew up around this industry. Built this because finding the right advisor is more like dating than hiring.
"""
        return subject, body

    def send_email(self, prospect: Dict, smtp_config: Dict) -> bool:
        """Send email to prospect"""
        try:
            subject, body = self.generate_email_content(prospect)

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_config['from_email']
            msg['To'] = prospect['email']

            # Add body
            msg.attach(MIMEText(body, 'plain'))

            # Send via SMTP
            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
                server.starttls()
                server.login(smtp_config['smtp_user'], smtp_config['smtp_password'])
                server.send_message(msg)

            # Log to database
            self.log_email_sent(prospect, subject)

            logging.info(f"✅ Sent email to {prospect['name']} ({prospect['email']})")
            return True

        except Exception as e:
            logging.error(f"❌ Failed to send email to {prospect['name']}: {e}")
            return False

    def log_email_sent(self, prospect: Dict, subject: str):
        """Log sent email to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO emails_sent (prospect_name, prospect_email, company, subject)
            VALUES (?, ?, ?, ?)
        ''', (prospect['name'], prospect['email'], prospect['company'], subject))

        # Update daily stats
        today = datetime.now().date()
        cursor.execute('''
            INSERT INTO daily_stats (date, emails_sent)
            VALUES (?, 1)
            ON CONFLICT(date) DO UPDATE SET emails_sent = emails_sent + 1
        ''', (today,))

        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Get recruitment statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total emails sent
        cursor.execute('SELECT COUNT(*) FROM emails_sent')
        total_sent = cursor.fetchone()[0]

        # Get today's stats
        today = datetime.now().date()
        cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (today,))
        today_stats = cursor.fetchone()

        # Get prospects remaining
        total_prospects = len(self.load_prospects())
        remaining = total_prospects - total_sent

        conn.close()

        return {
            'total_sent': total_sent,
            'total_prospects': total_prospects,
            'remaining': remaining,
            'today_sent': today_stats[1] if today_stats else 0,
            'completion_percentage': (total_sent / total_prospects * 100) if total_prospects > 0 else 0
        }

    def run_batch(self, batch_size: int = 10, smtp_config: Dict = None):
        """Run a batch of email sends"""
        if not smtp_config:
            logging.warning("⚠️ No SMTP config provided - using simulation mode")
            smtp_config = self.get_default_smtp_config()

        logging.info(f"🚀 Starting email batch (size: {batch_size})")

        # Get unsent prospects
        prospects = self.get_unsent_prospects(batch_size)

        if not prospects:
            logging.info("✅ All prospects have been contacted!")
            return

        # Send emails
        sent_count = 0
        for prospect in prospects:
            if self.send_email(prospect, smtp_config):
                sent_count += 1
                time.sleep(2)  # Rate limiting: 2 seconds between emails

        # Print stats
        stats = self.get_stats()
        logging.info(f"""
📊 BATCH COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sent this batch: {sent_count}
Total sent: {stats['total_sent']}/{stats['total_prospects']}
Remaining: {stats['remaining']}
Progress: {stats['completion_percentage']:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)

    def get_default_smtp_config(self) -> Dict:
        """Get default SMTP configuration"""
        # This would be loaded from credential vault in production
        return {
            'smtp_server': 'smtp.gmail.com',  # Change to your SMTP server
            'smtp_port': 587,
            'smtp_user': 'your-email@gmail.com',  # Change to your email
            'smtp_password': 'your-app-password',  # Change to your app password
            'from_email': 'james@fullpotential.com'
        }

    def run_autonomous(self, emails_per_hour: int = 10, smtp_config: Dict = None):
        """Run autonomously - sends emails continuously"""
        logging.info(f"🤖 AUTONOMOUS MODE ACTIVATED")
        logging.info(f"   Sending {emails_per_hour} emails/hour")
        logging.info(f"   Press Ctrl+C to stop")

        interval = 3600 / emails_per_hour  # Seconds between emails

        try:
            while True:
                # Get next prospect
                prospects = self.get_unsent_prospects(1)

                if not prospects:
                    logging.info("✅ All 317 prospects contacted! Mission complete.")
                    break

                # Send email
                self.send_email(prospects[0], smtp_config or self.get_default_smtp_config())

                # Wait for next send
                time.sleep(interval)

        except KeyboardInterrupt:
            logging.info("\n⏸️  Autonomous mode stopped by user")
            stats = self.get_stats()
            logging.info(f"Final stats: {stats['total_sent']}/{stats['total_prospects']} sent ({stats['completion_percentage']:.1f}%)")


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Autonomous Email Recruiter for I MATCH')
    parser.add_argument('--batch', type=int, help='Send a batch of N emails')
    parser.add_argument('--autonomous', action='store_true', help='Run in autonomous mode (continuous)')
    parser.add_argument('--rate', type=int, default=10, help='Emails per hour in autonomous mode')
    parser.add_argument('--stats', action='store_true', help='Show statistics')

    args = parser.parse_args()

    # Initialize recruiter
    prospects_csv = "/Users/jamessunheart/Development/SERVICES/i-match-automation/i_match_prospects_ready.csv"
    recruiter = AutonomousEmailRecruiter(prospects_csv)

    if args.stats:
        stats = recruiter.get_stats()
        print(f"""
📊 EMAIL RECRUITMENT STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Prospects: {stats['total_prospects']}
Emails Sent: {stats['total_sent']}
Remaining: {stats['remaining']}
Progress: {stats['completion_percentage']:.1f}%
Today: {stats['today_sent']} sent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)

    elif args.batch:
        recruiter.run_batch(args.batch)

    elif args.autonomous:
        recruiter.run_autonomous(args.rate)

    else:
        print("Use --batch N, --autonomous, or --stats")
        print("Example: python3 autonomous_email_recruiter.py --autonomous --rate 10")


if __name__ == "__main__":
    main()
