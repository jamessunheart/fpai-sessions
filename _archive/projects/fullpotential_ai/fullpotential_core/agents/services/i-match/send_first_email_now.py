#!/usr/bin/env python3
import sys
import json
sys.path.insert(0, '/Users/jamessunheart/Development/agents/services/ai-automation')
from marketing_engine.services.email_service_brevo import BrevoEmailService
import os

# Set Brevo API key
os.environ['BREVO_API_KEY'] = os.getenv('BREVO_API_KEY', 'YOUR_BREVO_API_KEY_HERE')

# Load prospects
with open('/Users/jamessunheart/Development/agents/services/i-match-automation/i_match_prospects_ready.json') as f:
    data = json.load(f)
    prospect = data['prospects'][0]['prospect']

# Initialize Brevo
brevo = BrevoEmailService()

# Generate email
first_name = prospect['first_name']
title = prospect['title']
company = prospect['company']
specialty = prospect.get('specialty', 'financial planning')

subject = f"AI matching for {title}s - qualified leads"

body_html = f"""<html><body>
<p>Hi {first_name},</p>

<p>I noticed your work as {title} at {company}.</p>

<p>Quick question: Would you be interested in qualified leads from people actively looking for financial advisors?</p>

<p>We're building <strong>I MATCH</strong> - an AI system that matches people to financial advisors based on compatibility (communication style, values, approach) rather than just credentials.</p>

<p><strong>The challenge:</strong> We need more advisors on the platform. Different specialties, different styles, so our AI can match people accurately.</p>

<p>If you're interested:</p>
<ul>
<li>Join as a matched advisor (free): <a href="http://198.54.123.234:8401">http://198.54.123.234:8401</a></li>
<li>Or help us recruit and earn 20% recurring: <a href="http://198.54.123.234:8401/static/contributors.html">Contributor Program</a></li>
</ul>

<p>Early stage experiment. Might work, might not. But if you're looking for better-fit clients, worth 5 minutes to check out.</p>

<p>Best,<br>
James (building I MATCH)</p>

<p><em>P.S. My dad's a CFP - grew up around this industry. Built this because finding the right advisor is more like dating than hiring.</em></p>
</body></html>"""

body_text = f"""Hi {first_name},

I noticed your work as {title} at {company}.

Quick question: Would you be interested in qualified leads from people actively looking for financial advisors?

We're building I MATCH - an AI system that matches people to financial advisors based on compatibility (communication style, values, approach) rather than just credentials.

The challenge: We need more advisors on the platform. Different specialties, different styles, so our AI can match people accurately.

If you're interested:
• Join as a matched advisor (free): http://198.54.123.234:8401
• Or help us recruit and earn 20% recurring: http://198.54.123.234:8401/static/contributors.html

Early stage experiment. Might work, might not. But if you're looking for better-fit clients, worth 5 minutes to check out.

Best,
James (building I MATCH)

P.S. My dad's a CFP - grew up around this industry. Built this because finding the right advisor is more like dating than hiring."""

# Derive email
email = f"{first_name.lower()}.{prospect['last_name'].lower()}@{company.lower().replace(' ', '').replace(',','')}.com"

print(f"Sending test email to: {prospect['first_name']} {prospect['last_name']}")
print(f"Email: {email}")
print(f"Subject: {subject}")
print("")

# Send email
result = brevo.send_email(
    to_email=email,
    to_name=f"{prospect['first_name']} {prospect['last_name']}",
    subject=subject,
    body_html=body_html,
    body_text=body_text,
    tags=['i-match-recruitment', 'financial-advisors']
)

print("Result:", json.dumps(result, indent=2))
