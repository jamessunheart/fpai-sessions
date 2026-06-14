"""
WhiteRock Blessings Engine - Email Service
SendGrid integration for transactional emails.
"""

import os
from datetime import datetime
from typing import Optional
from app.config import settings

# Optional SendGrid import
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False


class EmailService:
    """Service for sending transactional emails."""
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SENDGRID_FROM_EMAIL
        self.from_name = settings.SENDGRID_FROM_NAME
        self.blessing_footer = settings.BLESSING_EMAIL_FOOTER
        
        if self.api_key and SENDGRID_AVAILABLE:
            self.client = SendGridAPIClient(self.api_key)
        else:
            self.client = None
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email via SendGrid.
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.client:
            print(f"[EMAIL] Would send to {to_email}: {subject}")
            return True  # Simulate success for dev
        
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if text_content:
                message.add_content(Content("text/plain", text_content))
            
            response = self.client.send(message)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            print(f"[EMAIL] Failed to send: {e}")
            return False
    
    async def send_tithe_receipt(
        self,
        to_email: str,
        member_name: str,
        amount_cents: int,
        tithe_id: int,
        disclosure_version: str,
        created_at: datetime
    ) -> bool:
        """Send tithe receipt with compliant language."""
        amount_dollars = amount_cents / 100
        
        subject = f"WhiteRock Ministry - Tithe Receipt #{tithe_id}"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .header {{ background: #1e3a8a; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .receipt {{ background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .amount {{ font-size: 24px; color: #10b981; font-weight: bold; }}
                .disclaimer {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 12px; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>WhiteRock Church Trust</h1>
                <p>508(c)(1)(A) Religious Organization</p>
            </div>
            <div class="content">
                <p>Dear {member_name},</p>
                <p>Thank you for your sacred contribution to WhiteRock Ministry. 🙏</p>
                
                <div class="receipt">
                    <p><strong>Receipt #{tithe_id}</strong></p>
                    <p class="amount">${amount_dollars:,.2f} USD</p>
                    <p>Date: {created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                    <p>Disclosure Version: {disclosure_version}</p>
                </div>
                
                <div class="disclaimer">
                    <strong>⚠️ Important Disclosure</strong><br><br>
                    This contribution is an irrevocable charitable gift to WhiteRock Church Trust, 
                    a 508(c)(1)(A) religious organization. You receive no ownership interest, 
                    investment return, or contractual right to any benefit. Any community support 
                    provided is at the sole discretion of church leadership and is not guaranteed.
                </div>
                
                <p>Your contribution helps sustain our community and enables us to provide 
                discretionary blessings to members in need.</p>
                
                <p>May your generosity return to you manifold. 🌟</p>
            </div>
            <div class="footer">
                <p>WhiteRock Church Trust<br>
                508(c)(1)(A) Religious Organization<br>
                <a href="https://whiterock.us">whiterock.us</a></p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_content)
    
    async def send_decay_warning(
        self,
        to_email: str,
        member_name: str,
        current_balance: int,
        projected_decay: int,
        days_until_decay: int
    ) -> bool:
        """Send CORA decay warning email."""
        subject = "WhiteRock Ministry - CORA Vitality Notice"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .header {{ background: #1e3a8a; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .warning {{ background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .cora {{ font-size: 24px; color: #3b82f6; font-weight: bold; }}
                .action {{ background: #10b981; color: white; padding: 15px 30px; border-radius: 8px; display: inline-block; text-decoration: none; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>WhiteRock Ministry</h1>
            </div>
            <div class="content">
                <p>Dear {member_name},</p>
                
                <div class="warning">
                    <h3>⚠️ CORA Vitality Notice</h3>
                    <p>We noticed you haven't engaged with the WhiteRock community recently.</p>
                    <p>Your current CORA balance: <span class="cora">{current_balance} ☀️</span></p>
                    <p>In <strong>{days_until_decay} days</strong>, inactive CORA credits will begin 
                    to decay by 10% monthly (projected: -{projected_decay}).</p>
                </div>
                
                <h3>How to Maintain Your CORA Vitality:</h3>
                <ul>
                    <li>✅ Submit a tithe contribution</li>
                    <li>✅ Log service hours</li>
                    <li>✅ Participate in community events</li>
                    <li>✅ Check in through the member portal</li>
                </ul>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://whiterock.us/login" class="action">Visit Member Portal</a>
                </p>
                
                <p>CORA represents your standing in the WhiteRock community. 
                Active members maintain their vitality and are eligible for 
                discretionary community blessings when in need.</p>
                
                <p>We miss you and hope to see you soon! 🙏</p>
            </div>
            <div class="footer">
                <p>WhiteRock Church Trust - 508(c)(1)(A) Religious Organization</p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_content)
    
    async def send_blessing_status_update(
        self,
        to_email: str,
        member_name: str,
        blessing_id: int,
        new_status: str,
        message: str,
        include_footer: bool = True
    ) -> bool:
        """Send blessing status update email."""
        subject = f"WhiteRock Ministry - Blessing Request #{blessing_id} Update"
        
        status_colors = {
            "pending": "#f59e0b",
            "committee_review": "#3b82f6",
            "info_requested": "#f59e0b",
            "approved": "#10b981",
            "denied": "#ef4444",
            "disbursed": "#10b981",
            "closed": "#6b7280"
        }
        
        status_color = status_colors.get(new_status, "#6b7280")
        
        footer_html = f"""
        <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin-top: 30px; font-size: 12px;">
            {self.blessing_footer}
        </div>
        """ if include_footer and new_status in ["approved", "denied", "disbursed"] else ""
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .header {{ background: #1e3a8a; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .status {{ background: {status_color}; color: white; padding: 10px 20px; border-radius: 20px; display: inline-block; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>WhiteRock Ministry</h1>
            </div>
            <div class="content">
                <p>Dear {member_name},</p>
                
                <p>Your blessing request #{blessing_id} has been updated:</p>
                
                <p style="margin: 20px 0;">
                    <span class="status">{new_status.upper().replace('_', ' ')}</span>
                </p>
                
                <p>{message}</p>
                
                <p style="margin-top: 30px;">
                    <a href="https://whiterock.us/blessings/{blessing_id}">View Request Details</a>
                </p>
                
                {footer_html}
            </div>
            <div class="footer">
                <p>WhiteRock Church Trust - 508(c)(1)(A) Religious Organization</p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_content)
    
    async def send_welcome_email(
        self,
        to_email: str,
        member_name: str
    ) -> bool:
        """Send welcome email to new member."""
        subject = "Welcome to WhiteRock Ministry! 🙏"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .header {{ background: #1e3a8a; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .cta {{ background: #10b981; color: white; padding: 15px 30px; border-radius: 8px; display: inline-block; text-decoration: none; margin: 10px 5px; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Welcome to WhiteRock Ministry! 🙏</h1>
            </div>
            <div class="content">
                <p>Dear {member_name},</p>
                
                <p>Welcome to the WhiteRock community! We're blessed to have you join us on this journey.</p>
                
                <h3>Getting Started:</h3>
                <ol>
                    <li>Complete your member profile</li>
                    <li>Review and sign the community disclosure</li>
                    <li>Explore ways to participate in community life</li>
                    <li>Connect with fellow members</li>
                </ol>
                
                <h3>Your CORA Journey Begins:</h3>
                <p>As a new member, you start at the <strong>Seedling</strong> tier with the ability 
                to earn CORA vitality credits through tithes and community service. As your engagement 
                grows, so does your standing in the community.</p>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://whiterock.us/dashboard" class="cta">Visit Dashboard</a>
                    <a href="https://whiterock.us/community" class="cta" style="background: #3b82f6;">Join Community</a>
                </p>
                
                <p>May your time with WhiteRock be blessed! 🌟</p>
            </div>
            <div class="footer">
                <p>WhiteRock Church Trust - 508(c)(1)(A) Religious Organization<br>
                <a href="https://whiterock.us">whiterock.us</a></p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_content)



