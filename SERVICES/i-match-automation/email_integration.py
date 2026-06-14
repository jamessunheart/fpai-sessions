"""
Email Integration for I MATCH Automation Suite
Provides simplified email notification setup and testing
"""

import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class EmailConfig(BaseModel):
    """Email configuration"""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_name: str = "I MATCH - Full Potential AI"


class SimpleEmailNotifier:
    """Simplified email notification for I MATCH automation"""

    def __init__(self):
        self.config = EmailConfig(
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD")
        )

    def is_configured(self) -> bool:
        """Check if email is properly configured"""
        return bool(self.config.smtp_username and self.config.smtp_password)

    def get_setup_instructions(self) -> str:
        """Return setup instructions"""
        return """
🔧 EMAIL SETUP INSTRUCTIONS

To enable automated email notifications:

Option 1: Gmail (Recommended for testing)
─────────────────────────────────────────
1. Go to: https://myaccount.google.com/apppasswords
2. Sign in to your Google account
3. Create app password:
   - App: Mail
   - Device: Other (custom name: "I MATCH Automation")
4. Copy the 16-character password

5. Add to .env file:
   SMTP_USERNAME=your.email@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx  (the app password)

Option 2: SendGrid (Recommended for production)
────────────────────────────────────────────────
1. Sign up: https://sendgrid.com (free tier: 100 emails/day)
2. Create API key:
   - Settings → API Keys → Create API Key
   - Full Access permissions
3. Set up sender authentication (verify your domain)

4. Add to .env file:
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=SG.xxxxxxxxxx  (your SendGrid API key)

Test Configuration:
───────────────────
After setup, test with:
  python3 email_integration.py

This will send a test email to verify configuration.
"""

    def send_test_email(self, to_email: str) -> dict:
        """Send test email to verify configuration"""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Email not configured. Run get_setup_instructions()."
            }

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['Subject'] = "I MATCH Automation - Test Email"
            msg['From'] = f"{self.config.from_name} <{self.config.smtp_username}>"
            msg['To'] = to_email

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #667eea;">✅ Email Configuration Successful!</h2>
                <p>Your I MATCH automation email is now configured and working.</p>

                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                  <h3>Configuration Details:</h3>
                  <p><strong>SMTP Host:</strong> {self.config.smtp_host}</p>
                  <p><strong>SMTP Port:</strong> {self.config.smtp_port}</p>
                  <p><strong>From Email:</strong> {self.config.smtp_username}</p>
                </div>

                <p>You can now:</p>
                <ul>
                  <li>Send automated match notifications</li>
                  <li>Send provider lead alerts</li>
                  <li>Track email delivery in your dashboard</li>
                </ul>

                <p style="color: #666; margin-top: 30px;">
                  Built by Atlas - I MATCH Automation Suite
                </p>
              </body>
            </html>
            """

            text = f"""
EMAIL CONFIGURATION SUCCESSFUL!

Your I MATCH automation email is now configured and working.

Configuration:
- SMTP Host: {self.config.smtp_host}
- SMTP Port: {self.config.smtp_port}
- From Email: {self.config.smtp_username}

You can now send automated match notifications and track delivery.

Built by Atlas - I MATCH Automation Suite
            """

            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            # Send email
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            server.starttls()
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.send_message(msg)
            server.quit()

            return {
                "success": True,
                "message": f"Test email sent successfully to {to_email}",
                "from": self.config.smtp_username,
                "to": to_email
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "hint": "Check SMTP credentials and network connection"
            }

    def create_match_notification_email(
        self,
        customer_name: str,
        provider_name: str,
        provider_specialty: str,
        match_score: int
    ) -> str:
        """Create HTML email for match notification"""

        html = f"""
        <html>
          <head>
            <style>
              body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
              .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; padding: 30px; text-align: center; }}
              .content {{ padding: 30px; max-width: 600px; margin: 0 auto; }}
              .match-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px;
                           margin: 20px 0; border-left: 4px solid #667eea; }}
              .score {{ font-size: 36px; color: #667eea; font-weight: bold; }}
              .cta {{ background: #667eea; color: white; padding: 15px 30px;
                     text-decoration: none; border-radius: 5px; display: inline-block;
                     margin: 20px 0; }}
            </style>
          </head>
          <body>
            <div class="header">
              <h1>🎯 You've Been Matched!</h1>
            </div>

            <div class="content">
              <p>Hi {customer_name},</p>

              <p>Great news! Our AI has found a financial advisor who's an excellent match for your needs.</p>

              <div class="match-card">
                <h2>{provider_name}</h2>
                <p><strong>Specialty:</strong> {provider_specialty}</p>
                <div class="score">Match Score: {match_score}/10</div>
                <p style="color: #666; margin-top: 15px;">
                  This advisor's expertise aligns closely with what you're looking for.
                </p>
              </div>

              <h3>Why This Match?</h3>
              <p>Our AI analyzed your needs and {provider_name}'s expertise to identify this strong fit.
              A {match_score}/10 match means high compatibility in:</p>
              <ul>
                <li>Financial planning approach</li>
                <li>Expertise in your specific needs</li>
                <li>Communication style preferences</li>
              </ul>

              <a href="http://198.54.123.234:8401/matches" class="cta">
                View Match Details →
              </a>

              <p style="color: #666; margin-top: 30px; font-size: 14px;">
                Questions? Reply to this email or visit <a href="http://198.54.123.234:8401">I MATCH</a>
              </p>
            </div>
          </body>
        </html>
        """

        return html


# CLI Interface
if __name__ == "__main__":
    import sys

    print("📧 I MATCH Email Integration Setup")
    print("=" * 50)

    notifier = SimpleEmailNotifier()

    if not notifier.is_configured():
        print("\n⚠️  Email not configured yet!")
        print(notifier.get_setup_instructions())
        sys.exit(0)

    print("\n✅ Email is configured!")
    print(f"   From: {notifier.config.smtp_username}")
    print(f"   Host: {notifier.config.smtp_host}:{notifier.config.smtp_port}")
    print()

    # Send test email
    test_email = input("Enter email address for test (or press Enter to skip): ").strip()

    if test_email:
        print(f"\n📤 Sending test email to {test_email}...")
        result = notifier.send_test_email(test_email)

        if result["success"]:
            print(f"✅ {result['message']}")
            print("\nCheck your inbox! Email notifications are working.")
        else:
            print(f"❌ Failed: {result['error']}")
            if "hint" in result:
                print(f"   Hint: {result['hint']}")
    else:
        print("ℹ️  Skipping test email")

    print("\n" + "=" * 50)
    print("✅ Email integration ready!")
    print("\nTo use in your code:")
    print("  from email_integration import SimpleEmailNotifier")
    print("  notifier = SimpleEmailNotifier()")
    print("  notifier.send_test_email('customer@example.com')")
