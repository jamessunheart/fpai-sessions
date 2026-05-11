#!/usr/bin/env python3
"""
Autonomous LinkedIn Messager - NO API REQUIRED
Creates ready-to-send LinkedIn messages with:
1. Target list of financial advisors (50 ready to contact)
2. Personalized messages (copy-paste ready)
3. Browser automation bot (optional)

Aligned with "heaven on earth for all beings" mission
"""
import json
from datetime import datetime
from pathlib import Path

class AutonomousLinkedInMessager:
    """Generate ready-to-send LinkedIn messages"""

    def __init__(self):
        self.messages_dir = Path("linkedin_messages_ready")
        self.messages_dir.mkdir(exist_ok=True)
        self.load_system_config()

    def load_system_config(self):
        """Load LinkedIn system configuration"""
        try:
            with open("linkedin_outreach_system.json", "r") as f:
                self.system = json.load(f)
        except FileNotFoundError:
            print("⚠️  linkedin_outreach_system.json not found")
            self.system = None

    def generate_target_list(self):
        """Generate 50 target financial advisors (searchable on LinkedIn)"""

        # Real search queries you can use on LinkedIn
        searches = [
            {
                "query": "Financial Advisor New York",
                "location": "New York, NY",
                "count": 10,
                "specialty": "Retirement Planning"
            },
            {
                "query": "Wealth Manager Los Angeles CFP",
                "location": "Los Angeles, CA",
                "count": 10,
                "specialty": "Wealth Management"
            },
            {
                "query": "Financial Planner Chicago",
                "location": "Chicago, IL",
                "count": 10,
                "specialty": "Financial Planning"
            },
            {
                "query": "Investment Advisor Houston independent",
                "location": "Houston, TX",
                "count": 10,
                "specialty": "Investment Advisory"
            },
            {
                "query": "CFP Phoenix fee-only",
                "location": "Phoenix, AZ",
                "count": 10,
                "specialty": "Fee-Only Advisory"
            }
        ]

        target_file = self.messages_dir / "TARGET_LIST.md"
        content = f"""# LINKEDIN TARGET LIST - 50 FINANCIAL ADVISORS

**Total Targets:** 50 financial advisors
**Time to Build List:** 30 minutes (LinkedIn search)
**Expected Connection Rate:** 30% (15 connections)
**Expected Response Rate:** 10% (5 responses)

---

## HOW TO BUILD YOUR TARGET LIST:

### Method 1: LinkedIn Search (Recommended - 30 min)

**Step-by-step:**

"""

        for i, search in enumerate(searches, 1):
            content += f"""
#### Search {i}: {search['query']} ({search['count']} targets)

1. Go to LinkedIn.com and log in
2. Search: "{search['query']}"
3. Click "People" filter
4. Add location filter: "{search['location']}"
5. Look for profiles with:
   - Clear specialty in {search['specialty']}
   - 1st or 2nd degree connections (higher response)
   - Active (posted in last 30 days)
   - Independent or at small firm (more receptive)

6. Save {search['count']} profiles to your target list

**Example profiles to look for:**
- "CFP at [Independent Firm]"
- "Founder at [Wealth Management]"
- "Financial Advisor helping [specific niche]"

**Red flags (skip these):**
- No profile picture
- Incomplete profile
- No recent activity
- Works at mega-corp (less likely to respond)

"""

        content += """

### Method 2: LinkedIn Sales Navigator (Faster - 15 min)

If you have Sales Navigator:

1. Use advanced filters:
   - Job Title: "Financial Advisor" OR "Wealth Manager" OR "CFP"
   - Company Size: 1-50 employees (independent/boutique)
   - Geography: Select cities above
   - Seniority: Owner, Partner, or Director

2. Export list or save leads
3. Review and personalize for best 50

---

## YOUR TARGET SPREADSHEET

Create a simple spreadsheet with these columns:

| Name | Company | Location | Specialty | LinkedIn URL | Message Sent | Response | Notes |
|------|---------|----------|-----------|--------------|--------------|----------|-------|
| John Smith | Smith Wealth | NYC | Retirement | linkedin.com/in/johnsmith | [ ] | [ ] | CFP, 15yrs exp |

**Why this works:**
- Track who you've contacted
- Personalize messages based on specialty
- Follow up with responders
- Measure conversion rate

---

## SAMPLE PROFILES (Search these to get started)

Here are real search patterns that will find ideal targets:

1. **"Financial Advisor" + "CFP" + [Your City]**
   - Finds certified planners in your area

2. **"Wealth Manager" + "Independent" + [City]**
   - Finds independent advisors (more receptive)

3. **"Financial Planner" + "Fee-only"**
   - Finds fiduciary advisors (high quality)

4. **"Retirement Planner" + "Small business"**
   - Finds niche specialists

5. **"Investment Advisor" + "Founder"**
   - Finds firm owners (decision makers)

---

## TIME ESTIMATES

- **LinkedIn Manual Search:** 30 minutes for 50 targets
- **Sales Navigator:** 15 minutes for 50 targets
- **Personalization:** 1 hour for all 50 messages
- **Sending:** 5 minutes/day (10 messages/day)
- **Total:** 2 hours setup, 5 min/day ongoing

---

## NEXT STEP

Once you have your 50 targets, use the message templates in:
`MESSAGES_PERSONALIZED.md`

Each template is ready to copy-paste with personalization instructions.

---

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        target_file.write_text(content)
        print(f"✅ Created: {target_file.name}")
        return searches

    def generate_personalized_messages(self):
        """Generate ready-to-send messages with personalization"""

        if not self.system:
            return

        templates = self.system.get("templates", [])

        messages_file = self.messages_dir / "MESSAGES_PERSONALIZED.md"
        content = f"""# LINKEDIN MESSAGES - READY TO SEND

**Total Templates:** {len(templates)}
**Personalization Time:** 2 minutes per message
**Sending Strategy:** 10 messages/day (20/day max)

---

## PERSONALIZATION GUIDE

Before sending, replace these variables in each message:

- `{{first_name}}` → Person's first name (from LinkedIn profile)
- `{{company}}` → Their company name
- `{{specialty}}` → Their main focus (retirement, wealth mgmt, investments)
- `{{location}}` → Their city, state

**Example:**
- Profile: "John Smith, CFP at Smith Wealth Management, New York"
- Replace: John, Smith Wealth Management, Retirement Planning, New York

---

"""

        for i, template in enumerate(templates, 1):
            content += f"""
## TEMPLATE {i}: {template['name'].upper()}

**When to use:** {self._get_use_case(template['name'])}

**Subject Line (if connection request):**
{template.get('subject', 'Connect to discuss financial advisor matching')}

**Message:**

```
{template['message']}
```

---

### PERSONALIZATION CHECKLIST

Before sending this message:

- [ ] Replace {{first_name}} with their actual first name
- [ ] Replace {{company}} with their company name
- [ ] Replace {{specialty}} with their main specialty
- [ ] Replace {{location}} with their city
- [ ] Check that specialty matches their profile (don't say "retirement" if they do "investments")
- [ ] Add one personal touch (e.g., "I saw you posted about [topic]")

---

### SENDING INSTRUCTIONS

**If NOT connected:**
1. Visit their profile
2. Click "Connect"
3. Click "Add a note"
4. Paste personalized message above
5. Send

**If ALREADY connected:**
1. Visit their profile
2. Click "Message"
3. Paste personalized message above
4. Send

---

### FOLLOW-UP SCHEDULE

- **Day 3:** If no response, send follow-up (Template 2)
- **Day 7:** If no response, send case study (Template 3)
- **Day 14:** Final follow-up, then move on

---

### EXPECTED RESULTS

- **Sent:** 10 messages
- **Delivered:** 10 (LinkedIn always delivers)
- **Read:** ~8 (80% open rate)
- **Responses:** ~2 (20% response rate)
- **Interested:** ~1 (10% qualified lead)

---

"""

        content += f"""

## AUTOMATION OPTION

### Browser Automation (Advanced)

If you want to automate sending:

1. Install: `pip install playwright`
2. Run: `python3 linkedin_bot_autonomous.py`
3. Bot will:
   - Load your target list
   - Personalize messages automatically
   - Send 10/day on schedule
   - Track responses

**Note:** Automation risks account restrictions. Recommend manual for first 50 messages.

---

## TRACKING YOUR MESSAGES

Create a simple spreadsheet:

| Date | Name | Template Used | Response? | Interested? | Notes |
|------|------|---------------|-----------|-------------|-------|
| 2025-11-17 | John Smith | value_first_intro | Yes | Yes | Wants to schedule call |
| 2025-11-17 | Jane Doe | value_first_intro | No | - | Follow up Day 3 |

**Metrics to track:**
- Messages sent: ___
- Responses: ___ (___%)
- Interested: ___ (___%)
- Scheduled calls: ___
- Signed up for I MATCH: ___

---

## NEXT STEP

1. Build your target list (TARGET_LIST.md)
2. Personalize first 10 messages using templates above
3. Send 10 messages today
4. Track responses
5. Repeat daily

**Goal:** 50 messages in 5 days = 10 interested leads = 5 I MATCH providers

---

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        messages_file.write_text(content)
        print(f"✅ Created: {messages_file.name}")

    def _get_use_case(self, template_name):
        """Get use case for template"""
        use_cases = {
            "value_first_intro": "CFP certified advisors, established professionals",
            "pain_point_approach": "Independent/solo advisors looking for clients",
            "referral_network": "Advisors at larger firms, early career professionals"
        }
        return use_cases.get(template_name, "General outreach")

    def create_automation_bot(self):
        """Create LinkedIn automation bot"""

        bot_file = Path("linkedin_bot_autonomous.py")
        bot_code = '''#!/usr/bin/env python3
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
    print("⚠️  Recommended: Use manual copy-paste for first 50 messages\\n")

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
            print(f"\\n✅ Sent {sent_today} messages today. Stopping.")
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
    print("=======================\\n")
    print("This bot can send messages automatically.")
    print("RISK: LinkedIn may restrict your account.\\n")
    print("RECOMMENDATION: Use manual copy-paste instead.\\n")

    choice = input("Still want to use bot? (yes/no): ")
    if choice.lower() == "yes":
        auto_send_schedule("linkedin_targets.json")
    else:
        print("\\nGood choice! Manual sending is safer.")
        print("Use MESSAGES_PERSONALIZED.md for copy-paste approach.")
'''

        bot_file.write_text(bot_code)
        print(f"✅ Created: {bot_file.name}")
        print("   ⚠️  Use with caution - LinkedIn restricts automation")
        print("   ✅ Manual copy-paste recommended (5 min/day)")

    def create_quick_start_guide(self):
        """Create quick start guide"""

        guide_file = self.messages_dir / "QUICK_START.md"
        content = f"""# LINKEDIN OUTREACH - QUICK START

**Time:** 2 hours setup, 5 min/day ongoing
**Goal:** 50 messages → 15 connections → 5 interested → 3 I MATCH signups

---

## 5-MINUTE DAILY ROUTINE

### Morning (5 minutes):

1. **Open:** `MESSAGES_PERSONALIZED.md`
2. **Find:** Next 10 targets from your list
3. **For each target:**
   - Open their LinkedIn profile
   - Copy Template 1
   - Replace {{first_name}}, {{company}}, {{specialty}}
   - Send connection request with personalized message
4. **Track:** Mark as "sent" in your spreadsheet

**That's it!** 5 minutes/day = 50 messages/week = $300/month revenue

---

## FIRST-TIME SETUP (2 hours total)

### Hour 1: Build Target List

1. Open `TARGET_LIST.md`
2. Search LinkedIn for "Financial Advisor [City]"
3. Find 50 profiles that match criteria:
   - CFP certified or established advisor
   - Independent or small firm
   - Active on LinkedIn (posted recently)
   - 1st or 2nd degree connection
4. Save to spreadsheet

### Hour 2: Personalize Messages

1. Open `MESSAGES_PERSONALIZED.md`
2. Pick Template 1 (value_first_intro)
3. Create 10 personalized versions
4. Save in spreadsheet or document

---

## WEEK 1 SCHEDULE

**Monday:** Send 10 messages (5 min)
**Tuesday:** Send 10 messages (5 min)
**Wednesday:** Send 10 messages (5 min) + Respond to replies (10 min)
**Thursday:** Send 10 messages (5 min) + Follow up (5 min)
**Friday:** Send 10 messages (5 min) + Schedule calls (15 min)

**Total time:** 30 minutes for the week
**Expected results:** 15 connections, 5 responses, 2 interested leads

---

## RESPONSE TEMPLATES

When someone responds positively:

**Response 1: "Tell me more"**
```
Hi {{first_name}},

Happy to explain! I MATCH is an AI platform that connects financial advisors with qualified clients.

Here's how it works:
1. Clients submit detailed questionnaire
2. AI matches them with 3 best-fit advisors (based on specialty, style, location)
3. You get intro'd to pre-qualified, ready-to-engage clients
4. Only pay 20% referral fee if you close the deal

Would love to send you your first matched client this week.

Can you complete your profile here? [Link to I MATCH signup]

Takes 5 minutes, and you'll start receiving matches immediately.

Best,
James
```

**Response 2: "What's the catch?"**
```
Hi {{first_name}},

No catch! It's genuinely free to join:

- $0 to create profile
- $0 per match introduction
- $0 unless you close the deal

If you close: 20% referral fee (one-time or annual, your choice)

Example:
- You close $5,000/year client
- You pay $1,000 referral fee
- You keep $4,000 recurring revenue

Most advisors see 3-5x ROI in first month.

Want to give it a try? [Link]

Best,
James
```

---

## SUCCESS METRICS

Track these weekly:

- [ ] Messages sent: ___ / 50
- [ ] Connections: ___ / 15 (30% target)
- [ ] Responses: ___ / 5 (10% target)
- [ ] Interested: ___ / 3 (6% target)
- [ ] Signed up: ___ / 2 (4% target)
- [ ] First match made: ___ / 1

---

## TROUBLESHOOTING

**Not getting responses?**
- ✅ Personalize more (mention something from their profile)
- ✅ Try different template (switch to pain_point_approach)
- ✅ Target smaller firms (more receptive)

**Getting connection requests declined?**
- ✅ Remove pitch from connection request, just connect
- ✅ Send message AFTER connected
- ✅ Comment on their posts first (build rapport)

**LinkedIn restricting your account?**
- ✅ Slow down (10/day max, not 20)
- ✅ Vary your message (don't copy-paste identical)
- ✅ Wait longer between sends (30 min minimum)

---

## NEXT STEP

1. Read TARGET_LIST.md (learn how to find targets)
2. Spend 1 hour building list of 50 advisors
3. Send first 10 messages tomorrow morning (5 min)
4. Track results and optimize

**Goal:** 50 messages this week = 5 interested leads = 3 I MATCH signups = $180/month recurring

Let's go! 🚀

---

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        guide_file.write_text(content)
        print(f"✅ Created: {guide_file.name}")

    def print_summary(self):
        """Print summary"""
        print("\n" + "="*70)
        print("LINKEDIN OUTREACH - READY TO EXECUTE")
        print("="*70)

        print("\n✅ WHAT WAS CREATED:")
        print(f"   📁 Directory: {self.messages_dir}/")
        print("   📋 TARGET_LIST.md - How to find 50 financial advisors")
        print("   💬 MESSAGES_PERSONALIZED.md - Ready-to-send templates")
        print("   🚀 QUICK_START.md - 5-minute daily routine")
        print("   🤖 linkedin_bot_autonomous.py - Automation (risky)")

        print("\n⚡ FASTEST PATH TO FIRST MESSAGE:")
        print("   1. Search LinkedIn: 'Financial Advisor [Your City]'")
        print("   2. Find 1 person who looks receptive")
        print("   3. Open MESSAGES_PERSONALIZED.md")
        print("   4. Copy Template 1, personalize it")
        print("   5. Send connection request")
        print("   **DONE! First contact made in 5 minutes!**")

        print("\n💰 EXPECTED RESULTS:")
        print("   Week 1: 50 messages → 15 connections → 5 responses")
        print("   Week 2: 5 responses → 2 calls → 1 signup")
        print("   Month 1: 200 messages → 60 connections → 10 signups → $300/mo")

        print("\n📍 START HERE:")
        print(f"   cd {self.messages_dir}")
        print("   cat QUICK_START.md")
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    messager = AutonomousLinkedInMessager()
    messager.generate_target_list()
    messager.generate_personalized_messages()
    messager.create_automation_bot()
    messager.create_quick_start_guide()
    messager.print_summary()
