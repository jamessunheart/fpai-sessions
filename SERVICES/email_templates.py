"""
Professional Email Templates for I MATCH
Designed for SendGrid, AWS SES, or similar email services
"""

from typing import List, Dict
from datetime import datetime


class EmailTemplates:
    """Collection of email templates for customer journey"""

    # Brand colors and styling
    PRIMARY_COLOR = "#667eea"
    SUCCESS_COLOR = "#48bb78"
    BRAND_NAME = "Full Potential AI"
    SUPPORT_EMAIL = "hello@fullpotential.ai"
    LOGO_URL = "https://fullpotential.ai/logo.png"  # Update with actual logo

    @staticmethod
    def get_base_template(content: str) -> str:
        """Base HTML email template with branding"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{EmailTemplates.BRAND_NAME}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f7fafc;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 20px; text-align: center; background: linear-gradient(135deg, {EmailTemplates.PRIMARY_COLOR} 0%, #764ba2 100%); border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">
                                {EmailTemplates.BRAND_NAME}
                            </h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            {content}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px; text-align: center; background-color: #f7fafc; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0 0 10px; font-size: 14px; color: #718096;">
                                <strong>{EmailTemplates.BRAND_NAME}</strong><br>
                                AI-Powered Provider Matching
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #a0aec0;">
                                Questions? Reply to this email or contact {EmailTemplates.SUPPORT_EMAIL}
                            </p>
                            <p style="margin: 10px 0 0; font-size: 11px; color: #cbd5e0;">
                                <a href="{{unsubscribe_url}}" style="color: #cbd5e0; text-decoration: none;">Unsubscribe</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """

    @classmethod
    def intake_confirmation(cls, name: str, service_type: str, matches_count: int) -> Dict[str, str]:
        """Email #1: Immediate confirmation after intake submission"""
        first_name = name.split()[0]

        content = f"""
<h2 style="margin: 0 0 20px; color: #2d3748; font-size: 22px;">
    Great news, {first_name}! We're finding your perfect match 🎯
</h2>

<p style="margin: 0 0 16px; color: #4a5568; font-size: 16px; line-height: 1.6;">
    Thank you for choosing our AI-powered matching service. We've received your request for <strong>{service_type.replace('-', ' ').title()}</strong> services.
</p>

<div style="background: #f7fafc; border-left: 4px solid {cls.SUCCESS_COLOR}; padding: 16px 20px; margin: 24px 0; border-radius: 4px;">
    <p style="margin: 0; color: #2d3748; font-size: 15px;">
        <strong>✓ Your submission is confirmed</strong><br>
        <strong>✓ AI is analyzing {matches_count} potential providers</strong><br>
        <strong>✓ You'll get results within 24 hours</strong>
    </p>
</div>

<h3 style="margin: 24px 0 12px; color: #2d3748; font-size: 18px;">
    What happens next?
</h3>

<ol style="margin: 0 0 24px; padding-left: 20px; color: #4a5568; font-size: 15px; line-height: 1.8;">
    <li>Our AI analyzes your needs and ranks providers by compatibility</li>
    <li>We'll send your top 3 matches within 24 hours</li>
    <li>Review the matches and schedule free consultations</li>
    <li>Choose the provider that feels right for you</li>
</ol>

<div style="background: linear-gradient(135deg, {cls.PRIMARY_COLOR} 0%, #764ba2 100%); padding: 20px; margin: 24px 0; border-radius: 8px; text-align: center;">
    <p style="margin: 0; color: #ffffff; font-size: 16px; font-weight: 600;">
        Keep an eye on your inbox!<br>
        <span style="font-size: 14px; opacity: 0.9;">Your personalized matches are coming soon.</span>
    </p>
</div>

<p style="margin: 24px 0 0; color: #718096; font-size: 14px; line-height: 1.6;">
    Need immediate help? Reply to this email and a human will respond within 2 hours.
</p>
        """

        return {
            "subject": f"🎯 We're finding your perfect match, {first_name}!",
            "html": cls.get_base_template(content),
            "text": f"""
Hi {first_name},

Great news! We've received your request for {service_type.replace('-', ' ').title()} services.

✓ Your submission is confirmed
✓ AI is analyzing {matches_count} potential providers
✓ You'll get results within 24 hours

What happens next?

1. Our AI analyzes your needs and ranks providers
2. We'll send your top 3 matches within 24 hours
3. Review matches and schedule free consultations
4. Choose the provider that feels right

Keep an eye on your inbox!

Need help? Reply to this email.

Best,
{cls.BRAND_NAME} Team
            """
        }

    @classmethod
    def match_notification(cls, name: str, matches: List[Dict]) -> Dict[str, str]:
        """Email #2: Send matched providers (within 24 hours)"""
        first_name = name.split()[0]

        # Generate match cards HTML
        match_cards = []
        for i, match in enumerate(matches[:3], 1):
            score = match.get('match_score', 0)
            provider_name = match.get('provider_name', 'Provider')
            reasoning = match.get('match_reasoning', '')
            price_low = match.get('price_range_low', 0)
            price_high = match.get('price_range_high', 0)

            quality = "Excellent" if score >= 90 else "Very Good" if score >= 80 else "Good"
            score_color = "#48bb78" if score >= 90 else "#667eea" if score >= 80 else "#ed8936"

            match_cards.append(f"""
<div style="background: #ffffff; border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 16px 0;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 style="margin: 0; color: #2d3748; font-size: 18px;">
            #{i} - {provider_name}
        </h3>
        <span style="background: {score_color}; color: #ffffff; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 600;">
            {score}% Match
        </span>
    </div>

    <div style="background: #f7fafc; padding: 12px; border-radius: 4px; margin: 12px 0;">
        <p style="margin: 0; color: #4a5568; font-size: 14px; line-height: 1.5;">
            <strong>Why this is a {quality} match:</strong><br>
            {reasoning}
        </p>
    </div>

    <p style="margin: 8px 0; color: #718096; font-size: 14px;">
        <strong>Price Range:</strong> ${int(price_low):,} - ${int(price_high):,}
    </p>

    <a href="{{booking_url_{i}}}" style="display: inline-block; background: {cls.PRIMARY_COLOR}; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 8px;">
        Schedule Free Consultation →
    </a>
</div>
            """)

        content = f"""
<h2 style="margin: 0 0 20px; color: #2d3748; font-size: 22px;">
    {first_name}, we found your perfect matches! 🎉
</h2>

<p style="margin: 0 0 16px; color: #4a5568; font-size: 16px; line-height: 1.6;">
    Our AI has analyzed {len(matches)} providers and identified your top 3 matches based on expertise, compatibility, and value.
</p>

<div style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); padding: 16px 20px; margin: 24px 0; border-radius: 8px; text-align: center;">
    <p style="margin: 0; color: #ffffff; font-size: 16px; font-weight: 600;">
        ✓ All matches offer FREE initial consultations<br>
        <span style="font-size: 14px; opacity: 0.9;">No obligation - talk to each one and choose the best fit</span>
    </p>
</div>

<h3 style="margin: 24px 0 16px; color: #2d3748; font-size: 18px;">
    Your Top Matches
</h3>

{''.join(match_cards)}

<div style="background: #f7fafc; border-left: 4px solid {cls.PRIMARY_COLOR}; padding: 16px 20px; margin: 32px 0; border-radius: 4px;">
    <h4 style="margin: 0 0 8px; color: #2d3748; font-size: 16px;">
        💡 Pro Tip: Talk to all three
    </h4>
    <p style="margin: 0; color: #4a5568; font-size: 14px; line-height: 1.6;">
        Each provider brings something unique. Having 2-3 consultations helps you make the best decision and often uncovers new insights about your project.
    </p>
</div>

<p style="margin: 24px 0 0; color: #718096; font-size: 14px; line-height: 1.6;">
    Questions about these matches? Reply to this email and we'll help you choose.
</p>
        """

        return {
            "subject": f"🎉 {first_name}, your top {len(matches[:3])} matches are ready!",
            "html": cls.get_base_template(content),
            "text": f"""
Hi {first_name},

Great news! We found your perfect matches.

{chr(10).join([f"Match #{i+1}: {m.get('provider_name', 'Provider')} - {m.get('match_score', 0)}% match" for i, m in enumerate(matches[:3])])}

All matches offer FREE consultations. Click the links in the email to schedule.

Pro Tip: Talk to all three to make the best decision.

Questions? Just reply to this email.

Best,
{cls.BRAND_NAME} Team
            """
        }

    @classmethod
    def follow_up_no_action(cls, name: str, days: int = 3) -> Dict[str, str]:
        """Email #3: Follow-up if no action taken after match notification"""
        first_name = name.split()[0]

        content = f"""
<h2 style="margin: 0 0 20px; color: #2d3748; font-size: 22px;">
    {first_name}, did you get a chance to review your matches?
</h2>

<p style="margin: 0 0 16px; color: #4a5568; font-size: 16px; line-height: 1.6;">
    I wanted to check in - we sent your personalized provider matches {days} days ago, and I noticed you haven't scheduled any consultations yet.
</p>

<div style="background: #f7fafc; padding: 20px; margin: 24px 0; border-radius: 8px;">
    <h3 style="margin: 0 0 12px; color: #2d3748; font-size: 16px;">
        Need help deciding?
    </h3>
    <p style="margin: 0; color: #4a5568; font-size: 15px; line-height: 1.6;">
        I get it - choosing the right provider is a big decision. Here's what I can help with:
    </p>
    <ul style="margin: 12px 0 0; padding-left: 20px; color: #4a5568; font-size: 15px; line-height: 1.8;">
        <li>Questions about the matches or their backgrounds</li>
        <li>Want to see different providers? I can run a new search</li>
        <li>Need more context on pricing or services</li>
        <li>Just want to talk through your options</li>
    </ul>
</div>

<p style="margin: 24px 0 16px; color: #4a5568; font-size: 16px; line-height: 1.6;">
    <strong>Just reply to this email</strong> and let me know how I can help. I'm a real human and I'll respond personally within a few hours.
</p>

<p style="margin: 16px 0 0; color: #718096; font-size: 14px; line-height: 1.6;">
    PS - Still interested but not ready yet? No problem at all. I'll check back in a week or you can reach out anytime.
</p>
        """

        return {
            "subject": f"{first_name}, still looking for the right fit?",
            "html": cls.get_base_template(content),
            "text": f"""
Hi {first_name},

I wanted to check in - we sent your matches {days} days ago and noticed you haven't scheduled consultations yet.

Need help deciding? I can help with:
- Questions about the matches
- Want to see different providers
- Need more context on pricing/services
- Just want to talk through options

Just reply to this email. I'm a real human and respond within hours.

Still interested but not ready? No problem - reach out anytime.

Best,
{cls.BRAND_NAME} Team
            """
        }

    @classmethod
    def engagement_confirmed(cls, name: str, provider_name: str, deal_value: float) -> Dict[str, str]:
        """Email #4: Congratulations on confirming engagement"""
        first_name = name.split()[0]

        content = f"""
<h2 style="margin: 0 0 20px; color: #2d3748; font-size: 22px;">
    Congratulations, {first_name}! 🎉
</h2>

<p style="margin: 0 0 16px; color: #4a5568; font-size: 16px; line-height: 1.6;">
    We're thrilled to hear you're moving forward with <strong>{provider_name}</strong>! This is the start of something great.
</p>

<div style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); padding: 20px; margin: 24px 0; border-radius: 8px; text-align: center;">
    <p style="margin: 0; color: #ffffff; font-size: 18px; font-weight: 600;">
        Your project is now in expert hands
    </p>
</div>

<h3 style="margin: 24px 0 12px; color: #2d3748; font-size: 18px;">
    What happens next?
</h3>

<ol style="margin: 0 0 24px; padding-left: 20px; color: #4a5568; font-size: 15px; line-height: 1.8;">
    <li>{provider_name} will be in touch shortly to get started</li>
    <li>You'll work directly with them on your project</li>
    <li>We'll check in periodically to ensure everything's going well</li>
</ol>

<div style="background: #f7fafc; border-left: 4px solid {cls.PRIMARY_COLOR}; padding: 16px 20px; margin: 24px 0; border-radius: 4px;">
    <p style="margin: 0; color: #4a5568; font-size: 14px; line-height: 1.6;">
        <strong>Need our help?</strong><br>
        If any issues come up or you need support, we're here. Just reply to this email.
    </p>
</div>

<p style="margin: 24px 0 0; color: #718096; font-size: 14px; line-height: 1.6;">
    Thanks for trusting our matching service. We'd love to hear how it goes!
</p>
        """

        return {
            "subject": f"🎉 {first_name}, congrats on choosing {provider_name}!",
            "html": cls.get_base_template(content),
            "text": f"""
Hi {first_name},

Congratulations! We're thrilled you're moving forward with {provider_name}.

What happens next?
1. {provider_name} will be in touch shortly
2. You'll work directly with them
3. We'll check in to ensure everything's great

Need help? Just reply to this email.

Thanks for trusting our service!

Best,
{cls.BRAND_NAME} Team
            """
        }


# Example usage:
"""
# Send confirmation email
email_data = EmailTemplates.intake_confirmation(
    name="John Doe",
    service_type="church-formation",
    matches_count=4
)

# With SendGrid:
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email='hello@fullpotential.ai',
    to_emails='john@example.com',
    subject=email_data['subject'],
    html_content=email_data['html']
)

sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
response = sg.send(message)
"""
