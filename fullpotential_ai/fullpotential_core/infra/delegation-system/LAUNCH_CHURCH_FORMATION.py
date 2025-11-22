#!/usr/bin/env python3
"""
LAUNCH CHURCH FORMATION - Step-by-step Implementation
Combines LAUNCH_TODAY.md with Delegation System tracking

Use this to launch your church formation offer while tracking:
- Time spent on each task
- Money spent on tools/services
- What could be delegated to VAs

Run: python3 LAUNCH_CHURCH_FORMATION.py
"""

import sys
import os
from pathlib import Path

# Add delegation system to path
sys.path.insert(0, '/root/delegation-system')

try:
    from credential_vault import SpendingMonitor
    from time_tracker import TimeTracker
    from upwork_recruiter import TaskDelegator
    ON_SERVER = True
except ImportError:
    print("⚠️  Not on server - simulation mode")
    ON_SERVER = False


class LaunchTracker:
    """Track the church formation launch with delegation system"""

    def __init__(self):
        if ON_SERVER:
            self.spending = SpendingMonitor()
            self.timer = TimeTracker()
            self.delegator = TaskDelegator()
        else:
            print("Running in simulation mode (not on server)")

    def show_menu(self):
        """Interactive menu for launch tasks"""
        print("\n" + "="*60)
        print("🚀 CHURCH FORMATION LAUNCH - Implementation Tracker")
        print("="*60)
        print("\nHOUR 1: Landing Page + Payment (40 min)")
        print("  1. Create landing page with v0.dev")
        print("  2. Deploy to Vercel")
        print("  3. Setup Stripe payment")
        print("  4. Setup Calendly for consultations")
        print("\nHOUR 2: Traffic Generation (60 min)")
        print("  5. Create Facebook Ads campaign")
        print("  6. Create Google Ads campaign")
        print("  7. Post to Twitter/LinkedIn")
        print("  8. Post to Reddit")
        print("\nHOUR 3: AI Chatbot (60 min)")
        print("  9. Setup CustomGPT or Voiceflow chatbot")
        print("  10. Add to landing page")
        print("\nHOUR 4: Fulfillment (60 min)")
        print("  11. Create document templates with Claude")
        print("  12. Setup intake form")
        print("\nTRACKING")
        print("  s. Show spending summary")
        print("  t. Show time summary")
        print("  d. Show what could be delegated")
        print("  q. Quit")
        print("\nWhat would you like to work on? (1-12, s, t, d, q): ", end='')

    def task_1_v0_landing_page(self):
        """Create landing page with v0.dev"""
        print("\n" + "="*60)
        print("TASK 1: Create Landing Page with v0.dev")
        print("="*60)

        print("\n📋 Instructions:")
        print("\n1. Go to: https://v0.dev")
        print("\n2. Paste this prompt:")

        prompt = """
Create a high-converting landing page for church formation service:

**Headline:** Form Your 508(c)(1)(A) Church in 30 Days
**Subheadline:** Constitutional Protection, Tax Freedom, Privacy

**Hero Section:**
- Bold headline
- 3 key benefits with icons:
  ✅ No IRS registration needed (constitutional right)
  ✅ Tax-exempt status
  ✅ Complete privacy protection

**Social Proof:**
- "Trusted by 100+ freedom-seeking Americans"
- Testimonial placeholder

**Two CTAs:**
- Primary: "Book Free Consultation" (Calendly link)
- Secondary: "Get Started - $2,500" (Stripe payment link)

**How It Works (3 steps):**
1. Free consultation - understand your needs
2. Custom formation - we handle paperwork
3. Church formed - 30 days or less

**Pricing Section:**
- Free: Church formation guide (email capture)
- $2,500: Basic formation documents
- $15,000: Full service with legal review

**Trust Signals:**
- Money-back guarantee
- Secure payment (Stripe)
- Privacy protected

**FAQ Section:**
- What is 508(c)(1)(A)?
- Is this legal?
- How long does it take?
- What do I receive?

**Footer:**
- Contact info
- Legal disclaimer

Design: Clean, professional, trustworthy. Blue/white color scheme.
Mobile-responsive.
"""

        print(prompt)
        print("\n3. Click 'Generate'")
        print("\n4. Review and copy the code")

        if ON_SERVER:
            idx = self.timer.start_task("Create landing page with v0.dev")

        input("\n✅ Press Enter when you've generated the page...")

        if ON_SERVER:
            self.timer.complete_task(idx)

        print("\n✅ Landing page code ready!")
        print("\nNext: Deploy to Vercel (Task 2)")

    def task_2_deploy_vercel(self):
        """Deploy to Vercel"""
        print("\n" + "="*60)
        print("TASK 2: Deploy to Vercel")
        print("="*60)

        print("\n📋 Instructions:")
        print("\n1. Go to: https://vercel.com")
        print("2. Sign in with GitHub")
        print("3. Click 'Add New Project'")
        print("4. Import from repository OR:")
        print("   - Create new repository on GitHub")
        print("   - Push v0.dev code to it")
        print("   - Import to Vercel")
        print("\n5. Configure:")
        print("   - Framework: Next.js (auto-detected)")
        print("   - Root directory: ./")
        print("   - Build command: npm run build")
        print("   - Deploy")
        print("\n6. Get your URL: https://your-project.vercel.app")

        if ON_SERVER:
            idx = self.timer.start_task("Deploy to Vercel")

        input("\n✅ Press Enter when deployed...")

        url = input("\nEnter your Vercel URL: ")

        if ON_SERVER:
            self.timer.complete_task(idx)
            # Vercel is free for hobby projects
            self.spending.log_transaction(
                amount=0.00,
                merchant="Vercel",
                category="hosting",
                requester="you",
                description="Landing page deployment (free tier)"
            )

        print(f"\n✅ Landing page LIVE at: {url}")
        print("\nNext: Setup Stripe payment (Task 3)")

    def task_3_stripe_payment(self):
        """Setup Stripe payment"""
        print("\n" + "="*60)
        print("TASK 3: Setup Stripe Payment")
        print("="*60)

        print("\n📋 Instructions:")
        print("\n1. Go to: https://stripe.com")
        print("2. Create account (free)")
        print("3. Navigate to Products")
        print("4. Click 'Add Product'")
        print("\n5. Create products:")
        print("   Product 1:")
        print("   - Name: Church Formation - Basic")
        print("   - Price: $2,500 (one-time)")
        print("   - Description: Complete 508(c)(1)(A) formation documents")
        print("\n   Product 2:")
        print("   - Name: Church Formation - Full Service")
        print("   - Price: $15,000 (one-time)")
        print("   - Description: Full service with legal review")
        print("\n6. Get Payment Links:")
        print("   - For each product, click 'Create payment link'")
        print("   - Copy the links")
        print("\n7. Update landing page:")
        print("   - Replace CTA buttons with Stripe payment links")

        if ON_SERVER:
            idx = self.timer.start_task("Setup Stripe payment")

        input("\n✅ Press Enter when Stripe is setup...")

        basic_link = input("\nPaste Basic ($2,500) payment link: ")
        full_link = input("Paste Full Service ($15,000) payment link: ")

        if ON_SERVER:
            self.timer.complete_task(idx)
            self.spending.log_transaction(
                amount=0.00,
                merchant="Stripe",
                category="tools",
                requester="you",
                description="Payment processing setup (no monthly fee)"
            )

        print("\n✅ Payment processing ACTIVE!")
        print(f"\nBasic: {basic_link}")
        print(f"Full: {full_link}")
        print("\n⚠️  IMPORTANT: Add these links to your landing page!")
        print("\nNext: Setup Calendly (Task 4)")

    def task_4_calendly(self):
        """Setup Calendly for consultations"""
        print("\n" + "="*60)
        print("TASK 4: Setup Calendly for Free Consultations")
        print("="*60)

        print("\n📋 Instructions:")
        print("\n1. Go to: https://calendly.com")
        print("2. Sign up (free account)")
        print("3. Create event type:")
        print("   - Event name: Church Formation Consultation")
        print("   - Duration: 30 minutes")
        print("   - Location: Zoom (or Google Meet)")
        print("\n4. Set availability:")
        print("   - Choose your working hours")
        print("   - Buffer time: 15 min between meetings")
        print("\n5. Customize questions:")
        print("   - What's your main reason for forming a church?")
        print("   - What state are you in?")
        print("   - Current business/income situation?")
        print("   - Timeline to form?")
        print("\n6. Get your Calendly link")
        print("7. Add to landing page 'Book Free Consultation' button")

        if ON_SERVER:
            idx = self.timer.start_task("Setup Calendly")

        input("\n✅ Press Enter when Calendly is setup...")

        calendly_link = input("\nPaste your Calendly link: ")

        if ON_SERVER:
            self.timer.complete_task(idx)
            self.spending.log_transaction(
                amount=0.00,
                merchant="Calendly",
                category="tools",
                requester="you",
                description="Consultation booking (free tier)"
            )

        print(f"\n✅ Consultation booking ACTIVE!")
        print(f"\nLink: {calendly_link}")
        print("\n⚠️  Add this to your landing page!")
        print("\n" + "="*60)
        print("🎉 HOUR 1 COMPLETE!")
        print("="*60)
        print("\nYou now have:")
        print("  ✅ Landing page live on Vercel")
        print("  ✅ Stripe payment processing")
        print("  ✅ Calendly consultation booking")
        print("\n💡 Your landing page can now accept money!")
        print("\nNext: Hour 2 - Traffic Generation (Task 5-8)")

    def show_spending_summary(self):
        """Show spending summary"""
        if not ON_SERVER:
            print("\n⚠️  Spending tracking only available on server")
            return

        print("\n" + "="*60)
        print("💳 SPENDING SUMMARY")
        print("="*60)

        total = self.spending.get_spending_24h()
        by_cat = self.spending.get_spending_by_category(hours=168)  # Week

        print(f"\n24-hour spending: ${total:.2f}")
        print(f"\nBy category:")
        for cat, amount in by_cat.items():
            print(f"  {cat}: ${amount:.2f}")

        print(f"\nBudget remaining: ${5000 - total:.2f} (of $5,000 limit)")

    def show_time_summary(self):
        """Show time summary"""
        if not ON_SERVER:
            print("\n⚠️  Time tracking only available on server")
            return

        print("\n" + "="*60)
        print("⏱️  TIME SUMMARY")
        print("="*60)

        self.timer.get_summary()

    def show_delegation_opportunities(self):
        """Show what could be delegated"""
        print("\n" + "="*60)
        print("🤖 DELEGATION OPPORTUNITIES")
        print("="*60)

        print("\n✅ Can be delegated to VAs (human-required):")
        print("  • Stripe account setup + get API keys ($50, 24h)")
        print("  • Facebook Ads account + pixel setup ($50, 24h)")
        print("  • Google Ads account setup ($50, 24h)")
        print("  • Calendly setup + Zapier integration ($30, 24h)")
        print("  • Vercel deployment + custom domain ($40, 24h)")
        print("\n  Total: $220 VA cost, 24-48 hours completion")
        print("  Your time saved: ~2.5 hours = $250 value")

        print("\n✅ Can be done by AI (right now):")
        print("  • Landing page creation (v0.dev)")
        print("  • Ad copy generation (Claude)")
        print("  • Social media posts (Claude)")
        print("  • Document templates (Claude)")
        print("  • Email sequences (Claude)")

        print("\n⚠️  Must be done by you:")
        print("  • Strategy decisions")
        print("  • Customer consultations")
        print("  • Final approval of deliverables")

        if ON_SERVER:
            print("\n💡 To delegate tasks:")
            print("  python3 -c \"")
            print("  from upwork_recruiter import TaskDelegator")
            print("  delegator = TaskDelegator()")
            print("  task = delegator.delegate_task({")
            print("      'description': 'Setup Stripe + get API keys',")
            print("      'deliverables': ['Account ID', 'API Keys'],")
            print("      'deadline': '24 hours',")
            print("      'credentials': ['operations_card', 'operations_email'],")
            print("      'budget': 50")
            print("  })")
            print("  \"")

    def run(self):
        """Run the interactive launcher"""
        while True:
            self.show_menu()
            choice = input().strip().lower()

            if choice == '1':
                self.task_1_v0_landing_page()
            elif choice == '2':
                self.task_2_deploy_vercel()
            elif choice == '3':
                self.task_3_stripe_payment()
            elif choice == '4':
                self.task_4_calendly()
            elif choice == 's':
                self.show_spending_summary()
            elif choice == 't':
                self.show_time_summary()
            elif choice == 'd':
                self.show_delegation_opportunities()
            elif choice == 'q':
                print("\n✅ Exiting. Good luck with your launch! 🚀")
                break
            else:
                print(f"\n⚠️  Invalid choice: {choice}")

            input("\nPress Enter to continue...")


if __name__ == "__main__":
    launcher = LaunchTracker()
    launcher.run()
