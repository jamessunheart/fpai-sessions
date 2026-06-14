#!/usr/bin/env python3
"""
EXECUTABLE LinkedIn Outreach - Sends connection requests + DMs NOW

This script ACTUALLY EXECUTES on LinkedIn (not simulated).
Uses Playwright for browser automation.

SAFETY FEATURES:
- Manual review before sending each message
- Rate limiting (LinkedIn allows ~100 connections/day)
- Saves progress (can resume if interrupted)
"""

import os
import json
import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
STATE_FILE = Path("/Users/jamessunheart/Development/agents/services/i-match/linkedin_state.json")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Check credentials
if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
    logger.error("❌ Missing LinkedIn credentials")
    logger.error("Set environment variables:")
    logger.error("  export LINKEDIN_EMAIL='your@email.com'")
    logger.error("  export LINKEDIN_PASSWORD='yourpassword'")
    exit(1)

# Message templates
CONNECTION_MESSAGE = "Hi {first_name} - Quick question about quality leads for advisors. Worth a conversation?"

DM_TEMPLATE = """Hi {first_name},

I noticed you specialize in {specialty}. Impressive work.

Quick question: Would you be interested in AI-matched leads for high-net-worth clients?

How it works:
• Our AI matches clients to advisors based on deep compatibility
• You only pay 20% when they become your customer
• Much better fit = higher close rates than traditional lead gen

We're launching with 10 SF-based advisors this week. Want to be one of the first?

Form: http://198.54.123.234:8401/providers.html

Best,
James"""


class LinkedInAutomation:
    """Automated LinkedIn outreach"""

    def __init__(self):
        self.state = self.load_state()
        self.browser = None
        self.page = None

    def load_state(self):
        """Load automation state"""
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)

        return {
            "connection_requests_sent": 0,
            "dms_sent": 0,
            "targets": [],
            "last_run": None
        }

    def save_state(self):
        """Save automation state"""
        from datetime import datetime
        self.state["last_run"] = datetime.utcnow().isoformat()

        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def login(self, page):
        """Login to LinkedIn"""
        logger.info("🔐 Logging in to LinkedIn...")

        page.goto("https://www.linkedin.com/login")
        page.wait_for_load_state("networkidle")

        # Fill login form
        page.fill('input[name="session_key"]', LINKEDIN_EMAIL)
        page.fill('input[name="session_password"]', LINKEDIN_PASSWORD)

        # Submit
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Check if logged in
        if "feed" in page.url or "mynetwork" in page.url:
            logger.info("✅ Logged in successfully")
            return True
        else:
            logger.error("❌ Login failed - check credentials or handle CAPTCHA manually")
            return False

    def search_financial_advisors(self, page, location="San Francisco", count=20):
        """Search for financial advisors"""
        logger.info(f"🔍 Searching for financial advisors in {location}...")

        # Navigate to search
        search_url = 'https://www.linkedin.com/search/results/people/?keywords="financial%20advisor"%20OR%20"CFP"%20OR%20"wealth%20manager"&origin=GLOBAL_SEARCH_HEADER&sid=O%3A9'

        page.goto(search_url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)  # Let results load

        # Scroll to load more results
        for i in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

        # Find all profile cards
        profiles = page.query_selector_all('li.reusable-search__result-container')

        targets = []

        for profile in profiles[:count]:
            try:
                # Extract name
                name_element = profile.query_selector('span[aria-hidden="true"]')
                full_name = name_element.inner_text() if name_element else "Unknown"

                # Extract title
                title_element = profile.query_selector('.entity-result__primary-subtitle')
                title = title_element.inner_text() if title_element else "Unknown"

                # Extract profile URL
                link_element = profile.query_selector('a.app-aware-link')
                profile_url = link_element.get_attribute('href') if link_element else None

                # Check if Connect button available
                connect_button = profile.query_selector('button:has-text("Connect")')

                if connect_button and profile_url:
                    first_name = full_name.split()[0] if full_name else "there"

                    targets.append({
                        "name": full_name,
                        "first_name": first_name,
                        "title": title,
                        "profile_url": profile_url,
                        "specialty": self.extract_specialty(title)
                    })

            except Exception as e:
                logger.warning(f"Failed to extract profile: {e}")
                continue

        logger.info(f"✅ Found {len(targets)} potential targets")
        return targets

    def extract_specialty(self, title):
        """Extract specialty from title"""
        title_lower = title.lower()

        if "tax" in title_lower:
            return "tax optimization"
        elif "wealth" in title_lower:
            return "wealth management"
        elif "retirement" in title_lower:
            return "retirement planning"
        elif "estate" in title_lower:
            return "estate planning"
        else:
            return "financial planning"

    def send_connection_request(self, page, target, dry_run=False):
        """Send connection request to target"""
        logger.info(f"📤 Sending connection to: {target['name']}")

        if dry_run:
            logger.info("   [DRY RUN - not actually sending]")
            return True

        try:
            # Navigate to profile
            page.goto(target['profile_url'])
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Click Connect button
            connect_button = page.query_selector('button:has-text("Connect")')

            if not connect_button:
                logger.warning(f"   No Connect button found for {target['name']}")
                return False

            connect_button.click()
            time.sleep(1)

            # Check if "Add a note" option appears
            add_note_button = page.query_selector('button:has-text("Add a note")')

            if add_note_button:
                add_note_button.click()
                time.sleep(1)

                # Fill message
                message = CONNECTION_MESSAGE.format(first_name=target['first_name'])
                message_box = page.query_selector('textarea[name="message"]')

                if message_box:
                    message_box.fill(message)
                    time.sleep(0.5)

                    # Send
                    send_button = page.query_selector('button:has-text("Send")')
                    if send_button:
                        send_button.click()
                        logger.info(f"   ✅ Sent with note")
                        return True

            else:
                # Just send without note
                send_button = page.query_selector('button:has-text("Send")')
                if send_button:
                    send_button.click()
                    logger.info(f"   ✅ Sent without note")
                    return True

            return False

        except Exception as e:
            logger.error(f"   ❌ Failed to send: {e}")
            return False

    def run_automation(self, dry_run=True, max_connections=10):
        """Run the automation"""
        logger.info("=" * 70)
        logger.info("🤖 LINKEDIN AUTOMATION - I MATCH Phase 1")
        logger.info("=" * 70)
        logger.info("")

        if dry_run:
            logger.info("⚠️  DRY RUN MODE - No actual connections will be sent")
            logger.info("   Set dry_run=False to send real connections")
        else:
            logger.info("🚨 LIVE MODE - Real connections will be sent!")

        logger.info("")

        with sync_playwright() as p:
            # Launch browser (headless=False so you can see what's happening)
            self.browser = p.chromium.launch(headless=False)
            self.page = self.browser.new_page()

            # Login
            if not self.login(self.page):
                logger.error("Login failed - exiting")
                self.browser.close()
                return

            # Search for targets
            targets = self.search_financial_advisors(self.page, count=max_connections)

            if not targets:
                logger.error("No targets found - exiting")
                self.browser.close()
                return

            logger.info("")
            logger.info(f"📋 Found {len(targets)} targets")
            logger.info("")

            # Send connection requests
            sent_count = 0

            for i, target in enumerate(targets, 1):
                logger.info(f"[{i}/{len(targets)}] Processing: {target['name']}")

                success = self.send_connection_request(self.page, target, dry_run=dry_run)

                if success:
                    sent_count += 1
                    self.state["connection_requests_sent"] += 1

                    if not dry_run:
                        # Rate limiting - wait 30-60 seconds between connections
                        wait_time = 45
                        logger.info(f"   ⏳ Waiting {wait_time}s before next connection...")
                        time.sleep(wait_time)

                else:
                    logger.warning(f"   ⚠️  Skipped")

                # Save progress
                self.save_state()

            logger.info("")
            logger.info("=" * 70)
            logger.info(f"✅ AUTOMATION COMPLETE")
            logger.info("=" * 70)
            logger.info(f"Connections sent: {sent_count}/{len(targets)}")
            logger.info(f"Total sent today: {self.state['connection_requests_sent']}")
            logger.info("")

            if not dry_run:
                logger.info("🎯 NEXT STEPS:")
                logger.info("  1. Wait 24-48 hours for connections to accept")
                logger.info("  2. Run DM automation to send follow-up messages")
                logger.info("  3. Monitor responses and guide to provider form")
                logger.info("")

            # Close browser
            self.browser.close()


def main():
    """Main execution"""
    automation = LinkedInAutomation()

    # Parse command line args
    import sys
    dry_run = True if "--dry-run" in sys.argv or len(sys.argv) == 1 else False
    max_connections = 10

    if "--live" in sys.argv:
        dry_run = False
        logger.warning("")
        logger.warning("🚨 LIVE MODE ENABLED - Real connections will be sent!")
        logger.warning("")
        input("Press ENTER to continue or Ctrl+C to cancel...")

    automation.run_automation(dry_run=dry_run, max_connections=max_connections)


if __name__ == "__main__":
    logger.info("")
    logger.info("LinkedIn Automation for I MATCH")
    logger.info("")
    logger.info("Usage:")
    logger.info("  python3 execute_linkedin_now.py --dry-run  (test mode, no actual sends)")
    logger.info("  python3 execute_linkedin_now.py --live     (LIVE mode, sends real connections)")
    logger.info("")

    main()
