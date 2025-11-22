"""
Email Service for I MATCH
Sends match notifications to customers and providers
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
import os
from .config import settings


class EmailService:
    """Simple email service using SMTP"""

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username or os.getenv("SMTP_USERNAME")
        self.smtp_password = settings.smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = self.smtp_username
        self.from_name = "I MATCH - Full Potential AI"

    def _create_connection(self):
        """Create SMTP connection"""
        if not self.smtp_username or not self.smtp_password:
            raise ValueError("SMTP credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD in .env")

        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        server.starttls()
        server.login(self.smtp_username, self.smtp_password)
        return server

    def send_customer_match_notification(
        self,
        customer_email: str,
        customer_name: str,
        matches: List[Dict]
    ) -> bool:
        """
        Send match notification to customer

        Args:
            customer_email: Customer's email address
            customer_name: Customer's first name
            matches: List of match dictionaries with provider info

        Returns:
            bool: True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Your Top {len(matches)} Financial Advisor Matches"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = customer_email

            # Create email body
            html_body = self._create_customer_email_html(customer_name, matches)
            text_body = self._create_customer_email_text(customer_name, matches)

            # Attach both plain text and HTML
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with self._create_connection() as server:
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Error sending customer email: {e}")
            return False

    def send_provider_match_notification(
        self,
        provider_email: str,
        provider_name: str,
        customer: Dict,
        match_score: int,
        match_reasoning: str
    ) -> bool:
        """
        Send match notification to provider

        Args:
            provider_email: Provider's email address
            provider_name: Provider's name
            customer: Customer info dictionary
            match_score: Compatibility score (0-100)
            match_reasoning: AI explanation of why this is a good match

        Returns:
            bool: True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"New Lead: {customer['name']} ({match_score}% compatibility)"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = provider_email

            # Create email body
            html_body = self._create_provider_email_html(
                provider_name, customer, match_score, match_reasoning
            )
            text_body = self._create_provider_email_text(
                provider_name, customer, match_score, match_reasoning
            )

            # Attach both plain text and HTML
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with self._create_connection() as server:
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Error sending provider email: {e}")
            return False

    def _create_customer_email_html(self, customer_name: str, matches: List[Dict]) -> str:
        """Create HTML email for customer"""

        match_blocks = []
        for i, match in enumerate(matches, 1):
            provider = match['provider']
            match_blocks.append(f"""
                <div style="border: 2px solid #667eea; border-radius: 8px; padding: 20px; margin: 20px 0; background: #f8f9ff;">
                    <h3 style="color: #667eea; margin-top: 0;">
                        {i}️⃣ {provider['name']} - {match['match_score']}% Match ⭐
                    </h3>

                    <p><strong>Company:</strong> {provider.get('company', 'Independent')}</p>
                    <p><strong>Specialties:</strong> {', '.join(provider.get('specialties', ['Financial Planning']))}</p>
                    <p><strong>Experience:</strong> {provider.get('years_experience', 'N/A')} years</p>
                    <p><strong>Location:</strong> {provider.get('location_city', 'Remote')}, {provider.get('location_state', '')}</p>

                    <div style="background: #fff; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p style="margin: 0;"><strong>Why this is a great match:</strong></p>
                        <p style="margin: 10px 0 0 0;">{match['match_reasoning']}</p>
                    </div>

                    <p><strong>📧 Email:</strong> <a href="mailto:{provider['email']}">{provider['email']}</a></p>
                    {f"<p><strong>📞 Phone:</strong> {provider['phone']}</p>" if provider.get('phone') else ""}
                    {f"<p><strong>🌐 Website:</strong> <a href='{provider['website']}'>{provider['website']}</a></p>" if provider.get('website') else ""}
                </div>
            """)

        html = f"""
        <html>
        <head></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 10px;">
                    Your Perfect Advisor Matches
                </h1>

                <p>Hi {customer_name},</p>

                <p>Great news! Our AI has analyzed 100+ financial advisors and found your perfect matches.</p>

                <p>Here are your top {len(matches)} recommendations:</p>

                {''.join(match_blocks)}

                <div style="background: #f0f0f0; padding: 20px; border-radius: 8px; margin-top: 30px;">
                    <h3 style="margin-top: 0;">Next Steps:</h3>
                    <ol>
                        <li>Review each advisor above</li>
                        <li>Reach out to your top choices (we've notified them about you)</li>
                        <li>Schedule intro calls</li>
                        <li>Choose the best fit</li>
                    </ol>

                    <p><strong>Need help?</strong> Reply to this email anytime.</p>
                    <p><strong>Not satisfied?</strong> We'll find more matches at no cost.</p>
                </div>

                <p style="margin-top: 30px;">Best regards,<br>James<br>I MATCH - Full Potential AI</p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #666;">
                    This match was created using AI analysis + human review.
                    We earn a commission only if you engage an advisor (20% of their fee).
                    No cost to you.
                </p>
            </div>
        </body>
        </html>
        """

        return html

    def _create_customer_email_text(self, customer_name: str, matches: List[Dict]) -> str:
        """Create plain text email for customer"""

        match_text = []
        for i, match in enumerate(matches, 1):
            provider = match['provider']
            match_text.append(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{i}️⃣ {provider['name']} - {match['match_score']}% Match ⭐
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Company: {provider.get('company', 'Independent')}
Specialties: {', '.join(provider.get('specialties', ['Financial Planning']))}
Experience: {provider.get('years_experience', 'N/A')} years
Location: {provider.get('location_city', 'Remote')}, {provider.get('location_state', '')}

WHY THIS IS A GREAT MATCH:
{match['match_reasoning']}

CONTACT:
📧 Email: {provider['email']}
{"📞 Phone: " + provider['phone'] if provider.get('phone') else ""}
{"🌐 Website: " + provider['website'] if provider.get('website') else ""}
""")

        text = f"""
Hi {customer_name},

Great news! Our AI has analyzed 100+ financial advisors and found your perfect matches.

Here are your top {len(matches)} recommendations:

{''.join(match_text)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Review each advisor above
2. Reach out to your top choices (we've notified them about you)
3. Schedule intro calls
4. Choose the best fit

Need help? Reply to this email anytime.
Not satisfied? We'll find more matches at no cost.

Best regards,
James
I MATCH - Full Potential AI

---
This match was created using AI analysis + human review.
We earn a commission only if you engage an advisor (20% of their fee).
No cost to you.
"""

        return text

    def _create_provider_email_html(
        self,
        provider_name: str,
        customer: Dict,
        match_score: int,
        match_reasoning: str
    ) -> str:
        """Create HTML email for provider"""

        html = f"""
        <html>
        <head></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 10px;">
                    New High-Quality Lead
                </h1>

                <p>Hi {provider_name},</p>

                <p>Great news! We have a perfect-fit client for you.</p>

                <div style="border: 2px solid #48bb78; border-radius: 8px; padding: 20px; margin: 20px 0; background: #f0fff4;">
                    <h2 style="color: #48bb78; margin-top: 0;">
                        {customer['name']} - {match_score}% Compatibility ⭐
                    </h2>

                    <p><strong>Location:</strong> {customer.get('location_city', 'Not specified')}, {customer.get('location_state', '')}</p>
                    <p><strong>Service Needed:</strong> {customer.get('service_type', 'Financial Planning')}</p>

                    <div style="background: #fff; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p style="margin: 0;"><strong>Client's Needs:</strong></p>
                        <p style="margin: 10px 0 0 0;">{customer.get('needs_description', 'See details in intro call')}</p>
                    </div>

                    <div style="background: #fff; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p style="margin: 0;"><strong>Why This Is A Great Match:</strong></p>
                        <p style="margin: 10px 0 0 0;">{match_reasoning}</p>
                    </div>
                </div>

                <div style="background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107;">
                    <h3 style="margin-top: 0; color: #856404;">Next Steps:</h3>
                    <ol>
                        <li><strong>Reach out within 24 hours</strong> (response time matters!)</li>
                        <li>Reference their specific needs in your outreach</li>
                        <li>Offer a free 20-minute intro call</li>
                        <li>Let us know when they become a client</li>
                    </ol>
                </div>

                <div style="background: #e7f3ff; padding: 20px; border-radius: 8px; margin-top: 20px;">
                    <p style="margin: 0;"><strong>Suggested Intro Email:</strong></p>
                    <p style="margin: 10px 0 0 0; font-style: italic;">
                        "Hi {customer['name']},<br><br>

                        James from I MATCH shared your profile with me. I specialize in {customer.get('service_type', 'financial planning')}
                        and have helped many clients with {customer.get('needs_description', 'similar situations')[:50]}...<br><br>

                        I'd love to chat about how I can help with your goals. Would you be available for a 20-minute intro call this week?<br><br>

                        Best,<br>
                        {provider_name}"
                    </p>
                </div>

                <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <p style="margin: 0;"><strong>Client Contact:</strong></p>
                    <p style="margin: 10px 0 0 0;">
                        📧 {customer['email']}<br>
                        {f"📞 {customer['phone']}" if customer.get('phone') else ""}
                    </p>
                </div>

                <p style="margin-top: 30px;">Good luck! 🚀</p>

                <p>Best regards,<br>James<br>I MATCH - Full Potential AI</p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #666;">
                    <strong>Reminder:</strong> Commission is 20% of your fee when this client engages your services.
                    We'll send an invoice after engagement is confirmed. No upfront cost.
                </p>
            </div>
        </body>
        </html>
        """

        return html

    def _create_provider_email_text(
        self,
        provider_name: str,
        customer: Dict,
        match_score: int,
        match_reasoning: str
    ) -> str:
        """Create plain text email for provider"""

        text = f"""
Hi {provider_name},

Great news! We have a perfect-fit client for you.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{customer['name']} - {match_score}% Compatibility ⭐
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Location: {customer.get('location_city', 'Not specified')}, {customer.get('location_state', '')}
Service Needed: {customer.get('service_type', 'Financial Planning')}

CLIENT'S NEEDS:
{customer.get('needs_description', 'See details in intro call')}

WHY THIS IS A GREAT MATCH:
{match_reasoning}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Reach out within 24 hours (response time matters!)
2. Reference their specific needs in your outreach
3. Offer a free 20-minute intro call
4. Let us know when they become a client

SUGGESTED INTRO EMAIL:
"Hi {customer['name']},

James from I MATCH shared your profile with me. I specialize in {customer.get('service_type', 'financial planning')}
and have helped many clients with {customer.get('needs_description', 'similar situations')[:50]}...

I'd love to chat about how I can help with your goals. Would you be available for a 20-minute intro call this week?

Best,
{provider_name}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLIENT CONTACT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 {customer['email']}
{f"📞 {customer['phone']}" if customer.get('phone') else ""}

Good luck! 🚀

Best regards,
James
I MATCH - Full Potential AI

---
Reminder: Commission is 20% of your fee when this client engages your services.
We'll send an invoice after engagement is confirmed. No upfront cost.
"""

        return text


# Create singleton instance
email_service = EmailService()
