#!/usr/bin/env python3
"""
Autonomous LinkedIn Bot - CAREFUL: Can trigger account restrictions
Use at your own risk. Manual sending recommended for first 50 messages.
"""
from playwright.sync_api import sync_playwright
import time
import json

def send_linkedin_message(profile_url, message, headless=False):
    """Send message to LinkedIn profile"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        # Must be logged in to LinkedIn (use session cookies)
        print("⚠️  Make sure you're logged into LinkedIn in your default browser first")

        # Navigate to profile
        page.goto(profile_url)
        time.sleep(2)

        # Click "Message" button
        try:
            page.click('button:has-text("Message")')
            time.sleep(1)

            # Type message
            page.fill('div[contenteditable="true"]', message)
            time.sleep(1)

            # Send
            page.click('button:has-text("Send")')
            print(f"✅ Sent to {profile_url}")

        except Exception as e:
            print(f"❌ Failed to send: {e}")
            print("Try connecting first, or send manually")

        browser.close()

def auto_send_schedule(target_list_file, max_per_day=10):
    """Send messages according to schedule"""

    print("⚠️  WARNING: Automated LinkedIn messaging can trigger account restrictions")
    print("⚠️  LinkedIn allows ~20 messages/day. We'll send 10 to be safe.")
    print("⚠️  Recommended: Use manual copy-paste for first 50 messages\n")

    confirm = input("Continue with automation? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted. Use manual sending instead (MESSAGES_PERSONALIZED.md)")
        return

    # Load target list (you'll need to create this)
    with open(target_list_file) as f:
        targets = json.load(f)

    sent_today = 0
    for target in targets:
        if sent_today >= max_per_day:
            print(f"\n✅ Sent {sent_today} messages today. Stopping.")
            print("Run again tomorrow to send next batch.")
            break

        # Personalize message
        message = target['message_template'].format(
            first_name=target['first_name'],
            company=target['company'],
            specialty=target['specialty']
        )

        # Send
        send_linkedin_message(target['linkedin_url'], message)
        sent_today += 1

        # Wait 2-5 minutes between messages (avoid detection)
        wait_time = 120 + (sent_today * 30)  # Increasing delay
        print(f"⏳ Waiting {wait_time}s before next message...")
        time.sleep(wait_time)

if __name__ == "__main__":
    print("LinkedIn Autonomous Bot")
    print("=======================\n")
    print("This bot can send messages automatically.")
    print("RISK: LinkedIn may restrict your account.\n")
    print("RECOMMENDATION: Use manual copy-paste instead.\n")

    choice = input("Still want to use bot? (yes/no): ")
    if choice.lower() == "yes":
        auto_send_schedule("linkedin_targets.json")
    else:
        print("\nGood choice! Manual sending is safer.")
        print("Use MESSAGES_PERSONALIZED.md for copy-paste approach.")
