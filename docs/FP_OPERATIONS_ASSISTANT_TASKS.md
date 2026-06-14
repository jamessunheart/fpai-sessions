# Full Potential Operations Assistant - Setup Tasks

## 🎯 Mission
Set up automated email and SMS reminders so that when someone registers for the Weekly Call at fullpotential.com/call, they automatically receive:
1. Confirmation email with Zoom link
2. 24-hour reminder
3. 1-hour reminder (SMS if phone provided)
4. Post-call follow-up email

---

## 📊 Current State (Already Working)

✅ Registration form is live at: **https://fullpotential.com/call**
✅ When someone registers, James gets a **Telegram notification** instantly
✅ All registrations are saved to the server
✅ **Real-time spot counter** — shows "99 spots left" etc. (resets weekly)
✅ **Duplicate detection** — prevents same email registering twice per week
✅ **Referral system** — each registrant gets a unique referral link
✅ **Success page** with calendar links (Google, Apple, Outlook) + share buttons
✅ **Social sharing** — WhatsApp, Twitter, Facebook, Email share buttons with referral tracking
✅ **Open Graph tags** — proper preview when shared on Facebook/Twitter/LinkedIn
✅ **Sticky mobile CTA** — "Save My Spot" button follows mobile users as they scroll

**What's NOT working yet:**
❌ Registrants don't receive confirmation email
❌ No reminder emails/SMS
❌ No post-call follow-up

---

## 🛠️ Tools You'll Need

| Tool | Purpose | Cost |
|------|---------|------|
| **Kit (ConvertKit)** | Email sequences | Free up to 1,000 subscribers |
| **Zapier** | Connect form to Kit | Free for 100 tasks/month |
| **Zoom** | Host the calls | James has account |
| **Twilio** (optional) | SMS reminders | ~$0.01/text |

**Alternative to Kit:** Mailchimp (also free tier)

---

## 📋 TASK LIST

### Phase 1: Zoom Setup (15 minutes)
**Goal:** Create the recurring weekly call

- [ ] **1.1** Log into James's Zoom account
- [ ] **1.2** Create new meeting:
  - Name: "Full Potential Weekly Call"
  - Recurring: Every Thursday
  - Time: 5:00 PM Pacific Time (7 PM Central / 8 PM Eastern)
  - Duration: 60 minutes
  - Waiting room: ON
  - Registration: OFF (we handle it separately)
- [ ] **1.3** Copy the Zoom link (you'll need this for emails)
- [ ] **1.4** Save meeting ID and passcode

**Deliverable:** Zoom link ready to put in emails

---

### Phase 2: Kit (ConvertKit) Setup (30 minutes)
**Goal:** Create email account and templates

#### 2.1 Create Account (5 min)
- [ ] Go to https://kit.com (formerly ConvertKit)
- [ ] Sign up for free account
- [ ] Verify email
- [ ] Set sender name: "Full Potential"
- [ ] Set sender email: hello@fullpotential.com (or James's preferred email)

#### 2.2 Create Subscriber Tag (5 min)
- [ ] Go to Subscribers → Tags
- [ ] Create tag: "Weekly Call Registrant"

#### 2.3 Create Email Templates (20 min)

**Template 1: Confirmation Email**
```
Subject: You're in! 🎉 Weekly Call Details Inside

Hi {first_name}!

You're registered for the Full Potential Weekly Call.

📅 When: This Thursday at 5:00 PM Pacific (7 PM Central / 8 PM Eastern)
⏱️ Duration: 60 minutes
💻 Where: Zoom (link below)

👉 JOIN THE CALL: [ZOOM LINK HERE]

Meeting ID: [ID]
Passcode: [PASSCODE]

What to expect:
• Live guidance on your biggest goal
• Q&A time for your questions
• See AI-powered support in action
• Leave with your next concrete step

Pro tip: Come with ONE goal or challenge you want clarity on.

See you Thursday!

— James & the Full Potential Team

P.S. Add this to your calendar so you don't forget!
```

**Template 2: 24-Hour Reminder**
```
Subject: Tomorrow: Your Weekly Call 📞

Hi {first_name}!

Quick reminder — the Weekly Call is TOMORROW.

📅 Thursday at 5:00 PM Pacific (7 PM Central / 8 PM Eastern)
💻 Zoom link: [ZOOM LINK HERE]

🚗 Listen from your car, your couch, or your desk — just show up.

Come with your biggest goal or question ready.

See you there!

— Full Potential
```

**Template 3: 1-Hour Reminder**
```
Subject: Starting in 1 hour! 🚀

Hi {first_name}!

The Full Potential Hour starts in 1 HOUR.

👉 JOIN NOW: [ZOOM LINK HERE]

Driving? Just listen in — it's commute-friendly.
See you soon!

— Full Potential
```

**Template 4: Post-Call Follow-Up (send day after)**
```
Subject: Thanks for joining! Here's what's next

Hi {first_name}!

Thanks for being on yesterday's Weekly Call!

Here's the recording: [LINK - add later]

Loved it and want more support? Here are your options:

🌱 Weekly Group ($97/mo)
Join every weekly call + AI companion + private community
→ Reply "GROUP" to learn more

🚀 1-on-1 Coaching ($500+/mo)  
Personal coaching + custom strategy + direct access
→ Reply "COACHING" to learn more

Or just reply to this email with any questions!

To your full potential,
— James
```

**Deliverable:** 4 email templates ready in Kit

---

### Phase 3: Zapier Automation (45 minutes)
**Goal:** Connect registration form to Kit emails

#### 3.1 Create Zapier Account (5 min)
- [ ] Go to https://zapier.com
- [ ] Sign up for free account
- [ ] Verify email

#### 3.2 Create Webhook (10 min)
- [ ] Create new Zap
- [ ] Trigger: "Webhooks by Zapier" → "Catch Hook"
- [ ] Copy the webhook URL (looks like: https://hooks.zapier.com/hooks/catch/xxxxx/)
- [ ] **IMPORTANT:** Send this webhook URL to the developer to add to the registration form

#### 3.3 Set Up Kit Connection (10 min)
- [ ] Add action: "Kit (ConvertKit)" → "Add Subscriber"
- [ ] Connect your Kit account
- [ ] Map fields:
  - Email → `email` from webhook
  - First Name → `firstName` from webhook
- [ ] Add tag: "Weekly Call Registrant"

#### 3.4 Send Confirmation Email (10 min)
- [ ] Add another action: "Kit" → "Send Email"
- [ ] Select your Confirmation Email template
- [ ] Test the Zap

#### 3.5 Set Up Reminder Sequence (10 min)
In Kit, create an Automation:
- [ ] Trigger: When subscriber added with tag "Weekly Call Registrant"
- [ ] Wait until: Thursday 5:00 PM PT - 24 hours (so Wednesday 5pm PT)
  - [ ] Send: 24-hour reminder email
  - [ ] Wait until: Thursday 4:00 PM PT
- [ ] Send: 1-hour reminder email
- [ ] Wait: 1 day after call
- [ ] Send: Post-call follow-up

**Deliverable:** Zap is live and tested

---

### Phase 4: Connect to Website (15 minutes)
**Goal:** Make the registration form send data to Zapier

**You need to tell the developer:**
1. The Zapier webhook URL
2. Ask them to add it to the form submission

**Or if you have server access:**
Update `/opt/fpai/weekly-call-registrations.py` to also POST to Zapier webhook.

---

### Phase 5: Testing (30 minutes)
**Goal:** Verify everything works end-to-end

- [ ] **5.1** Submit a test registration at fullpotential.com/call
- [ ] **5.2** Verify James gets Telegram notification
- [ ] **5.3** Verify test email receives confirmation
- [ ] **5.4** Check Kit shows new subscriber with tag
- [ ] **5.5** Manually trigger reminder emails to test
- [ ] **5.6** Document any issues

**Deliverable:** Full system tested and working

---

### Phase 6: SMS Reminders (Optional) (45 minutes)
**Goal:** Send text message reminders

#### 6.1 Twilio Setup
- [ ] Create Twilio account at twilio.com
- [ ] Get phone number (~$1/month)
- [ ] Note Account SID and Auth Token

#### 6.2 Zapier SMS Action
- [ ] In your Zap, add: "Twilio" → "Send SMS"
- [ ] Connect Twilio account
- [ ] Set up 1-hour reminder SMS:
```
Full Potential Weekly Call starts in 1 hour!

Join: [ZOOM LINK]

See you soon! 🌱
```

---

## ⏱️ Time Estimates Summary

| Phase | Task | Time |
|-------|------|------|
| 1 | Zoom Setup | 15 min |
| 2 | Kit Setup + Templates | 30 min |
| 3 | Zapier Automation | 45 min |
| 4 | Connect to Website | 15 min |
| 5 | Testing | 30 min |
| 6 | SMS (Optional) | 45 min |
| **TOTAL** | | **2-3 hours** |

---

## 📞 When You Need Help

**For email/Zapier questions:**
- Kit Help: https://help.kit.com
- Zapier Help: https://help.zapier.com

**For website/technical issues:**
- Contact the developer (via James)
- The registration API is at: `https://fullpotential.com/api/intake/`

**For Zoom questions:**
- Ask James for account access

---

## ✅ Definition of Done

The setup is complete when:
1. [ ] Someone registers → Gets confirmation email within 1 minute
2. [ ] Wednesday 7pm → Gets 24-hour reminder
3. [ ] Thursday 6pm → Gets 1-hour reminder
4. [ ] Friday → Gets post-call follow-up
5. [ ] James continues to get Telegram notifications
6. [ ] All registrations are tracked in Kit

---

## 🔐 Accounts Needed

| Service | Who Creates | Who Has Access |
|---------|-------------|----------------|
| Kit | Assistant | Assistant + James |
| Zapier | Assistant | Assistant |
| Zoom | James (existing) | James shares link |
| Twilio | Assistant | Assistant |

---

## 📝 Notes for Developer

When the assistant has the Zapier webhook URL, update the registration handler to also POST to Zapier:

```python
# Add to /opt/fpai/weekly-call-registrations.py
ZAPIER_WEBHOOK = "https://hooks.zapier.com/hooks/catch/xxxxx/xxxxx/"

def send_to_zapier(data):
    try:
        requests.post(ZAPIER_WEBHOOK, json=data, timeout=10)
    except:
        pass
```

---

**Document Created:** February 9, 2026
**Last Updated:** February 9, 2026
**Owner:** Full Potential Operations Assistant

