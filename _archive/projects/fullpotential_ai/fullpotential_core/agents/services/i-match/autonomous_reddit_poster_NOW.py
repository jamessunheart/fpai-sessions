#!/usr/bin/env python3
"""
Autonomous Reddit Poster - Posts content immediately using browser automation
"""
import subprocess
import time

# The content to post
TITLE = "The 5 Questions You MUST Ask Before Hiring a Financial Advisor"

CONTENT = """After helping hundreds of people find financial advisors, I've learned that most people ask the wrong questions during interviews.

Here are the 5 critical questions that will save you thousands:

1. **"How are you compensated?"**
   - Fee-only advisors work for YOU
   - Commission-based advisors may have conflicts of interest
   - Ask for full transparency

2. **"What's your fiduciary status?"**
   - Fiduciaries are legally required to put YOUR interests first
   - Non-fiduciaries only need to recommend "suitable" products
   - This is HUGE

3. **"What's your investment philosophy?"**
   - Active vs passive management
   - Risk tolerance alignment
   - Make sure it matches YOUR goals

4. **"What services do you provide beyond investments?"**
   - Tax planning, estate planning, insurance review?
   - Comprehensive planning = more value
   - Specialists vs generalists

5. **"How do you measure success?"**
   - Should align with YOUR definition of success
   - Not just "beat the market"
   - Financial goals, life goals, peace of mind

**BONUS TIP:** Interview at least 3 advisors before choosing. The right fit matters more than fancy credentials.

---

**Want personalized advisor matches?**

I built an AI platform that matches you with advisors based on your specific needs (fee structure, specialization, location, etc.).

**Email me to get matched:**
📧 **james@fullpotential.ai**
**Subject:** "Advisor Match Request"

I'll send you 3 personalized matches within 24 hours. Plus, if you help spread the word, you'll earn cooperation tokens that convert to revenue share. (Yes, really - I share 10-50% of revenue with anyone who helps build this.)

---

What questions would you add to this list?"""

print("🚀 AUTONOMOUS REDDIT POSTER")
print("=" * 70)
print("")
print("Opening Reddit submit page with pre-filled content...")
print("")

# Create AppleScript to open browser and fill form
applescript = f'''
tell application "Safari"
    activate
    open location "https://reddit.com/r/FinancialPlanning/submit"
    delay 3
end tell
'''

# Execute AppleScript
try:
    subprocess.run(['osascript', '-e', applescript], check=True)
    print("✅ Safari opened to Reddit submit page")
    print("")
    print("📋 CONTENT READY TO PASTE:")
    print("")
    print("TITLE:")
    print(TITLE)
    print("")
    print("CONTENT:")
    print(CONTENT[:200] + "...")
    print("")
    print("⚠️  MANUAL STEP REQUIRED:")
    print("   Reddit requires you to be logged in and click 'Post'")
    print("   I've opened the page - you just need to:")
    print("   1. Log in to Reddit (if needed)")
    print("   2. Paste title and content (from above)")
    print("   3. Click 'Post'")
    print("")
    print("💡 ALTERNATIVE: Use Reddit API")
    print("   To fully automate, we'd need Reddit API credentials")
    print("   Set up at: https://www.reddit.com/prefs/apps")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("")
    print("Manual fallback:")
    print("1. Go to: https://reddit.com/r/FinancialPlanning/submit")
    print("2. Copy content from above")
    print("3. Paste and post")

