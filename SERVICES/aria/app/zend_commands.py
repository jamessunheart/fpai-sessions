"""
Aria Zend Commands Module
==========================

Natural language processing for Zend Money operations.
Integrates with zend-payments (external settlement) and zend-wallet (UC credits).

Commands supported:
- Invoice creation: "Invoice $23.50 for 2 lattes"
- UC balance: "What's my balance?" / "UC balance"
- Send UC: "Send $50 to @alice" / "Zend 100 UC to bob@email.com"
- Payment status: "Status of abc123"
- Create payment links: "Create a payment link for $100"

Per docs/protocols/ZEND_REGENERATIVE_SPEC.md
"""

import re
import httpx
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger("aria.zend_commands")

# API URLs (configurable via environment)
import os
ZEND_PAYMENTS_URL = os.getenv("ZEND_PAYMENTS_URL", "http://127.0.0.1:8581")
ZEND_WALLET_URL = os.getenv("ZEND_WALLET_URL", "http://127.0.0.1:8580")


class ZendCommands:
    """Process Zend Money natural language commands."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
    
    async def close(self):
        await self.client.aclose()
    
    def extract_amount(self, text: str) -> Optional[float]:
        """Extract dollar/UC amount from text."""
        patterns = [
            r'\$([\d,]+\.?\d*)',  # $100, $1,000.50
            r'([\d,]+\.?\d*)\s*(?:dollars?|USD|usd|UC|uc)',  # 100 dollars, 50 UC
            r'([\d,]+\.?\d*)',  # Plain number as fallback
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.replace(',', ''))
            if match:
                try:
                    amount = float(match.group(1))
                    if 0 < amount <= 100000:  # Sanity check
                        return amount
                except ValueError:
                    continue
        
        return None
    
    def extract_recipient(self, text: str) -> tuple[Optional[str], str]:
        """
        Extract recipient from text.
        Returns (recipient, recipient_type: 'member'|'email'|'phone'|'unknown')
        """
        # Email pattern
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            return email_match.group(0), "email"
        
        # Phone pattern
        phone_match = re.search(r'\+?\d[\d\s\-\(\)]{7,}', text)
        if phone_match:
            return phone_match.group(0).strip(), "phone"
        
        # @handle pattern
        handle_match = re.search(r'@([a-zA-Z0-9_\-]{3,})', text)
        if handle_match:
            return handle_match.group(1), "member"
        
        # "to <name>" pattern
        to_match = re.search(r'to\s+([a-zA-Z][a-zA-Z0-9_\-]{2,})', text, re.IGNORECASE)
        if to_match:
            return to_match.group(1), "member"
        
        return None, "unknown"
    
    def extract_description(self, text: str) -> str:
        """Extract description/note from text."""
        # Remove amount and recipient, keep the rest
        cleaned = text
        cleaned = re.sub(r'\$([\d,]+\.?\d*)', '', cleaned)
        cleaned = re.sub(r'([\d,]+\.?\d*)\s*(?:dollars?|USD|usd|UC|uc)', '', cleaned)
        cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', cleaned)
        cleaned = re.sub(r'@[a-zA-Z0-9_\-]+', '', cleaned)
        cleaned = re.sub(r'\+?\d[\d\s\-\(\)]{7,}', '', cleaned)
        
        # Remove command words
        for word in ['invoice', 'send', 'zend', 'pay', 'for', 'to', 'create', 'link']:
            cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:200] if cleaned else ""
    
    async def process_zend_command(self, 
                                   message: str, 
                                   user_id: str,
                                   api_key: Optional[str] = None) -> Optional[str]:
        """
        Process Zend-related commands and return response.
        Returns None if message is not a Zend command.
        
        Supported:
        - Invoice: "Invoice $23.50 for 2 lattes"
        - Balance: "balance", "UC balance", "my balance"
        - Send: "Send $50 to @alice", "Zend 100 UC to bob@email.com"
        - Status: "Status abc123", "Check payment xyz"
        - Link: "Create payment link for $100"
        """
        msg_lower = message.lower().strip()
        
        # Headers for authenticated requests
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        headers["X-Zend-Admin-Key"] = os.getenv("ZEND_ADMIN_KEY", "")
        
        # ========== INVOICE CREATION ==========
        
        if "invoice" in msg_lower or ("create" in msg_lower and "payment" in msg_lower):
            amount = self.extract_amount(message)
            if not amount:
                return "❌ Please specify an amount. Example: 'Invoice $23.50 for 2 lattes'"
            
            description = self.extract_description(message)
            
            try:
                resp = await self.client.post(
                    f"{ZEND_PAYMENTS_URL}/api/invoices",
                    json={
                        "merchant_id": user_id,
                        "total": amount,
                        "currency": "USD",
                        "note": description or "Payment request",
                        "commons_tithe_pct": 0,
                        "expires_in_minutes": 30,
                    },
                    headers=headers,
                    timeout=10.0
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    return (
                        f"✅ **Invoice Created!**\n\n"
                        f"💰 Amount: ${amount:.2f}\n"
                        f"📝 Description: {description or 'Payment request'}\n\n"
                        f"🔗 **ZendLink:** {data.get('zend_link')}\n\n"
                        f"Share this link with your customer to receive payment.\n"
                        f"⏰ Expires in 30 minutes\n\n"
                        f"_Zend to Ascend_ ✨"
                    )
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Invoice creation failed: {error}"
            except httpx.ConnectError:
                return "❌ Zend Payments service is not available. Please try again later."
            except Exception as e:
                logger.error(f"Invoice creation error: {e}")
                return f"❌ Error creating invoice: {str(e)}"
        
        # ========== UC BALANCE ==========
        
        if "balance" in msg_lower or ("my" in msg_lower and "uc" in msg_lower) or ("check" in msg_lower and "uc" in msg_lower):
            try:
                resp = await self.client.get(
                    f"{ZEND_WALLET_URL}/api/zend/wallet/{user_id}",
                    headers=headers,
                    timeout=10.0
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    uc_balance = data.get("uc_balance", 0)
                    unlocked = data.get("unlocked", [])
                    
                    response = f"💎 **ZEND UC Balance**\n\n"
                    response += f"🪙 **{uc_balance:.2f} UC**\n\n"
                    
                    if unlocked:
                        response += "✨ **Unlocked:**\n"
                        for u in unlocked:
                            response += f"  • {u}\n"
                    
                    response += "\n_UC Credits are prepaid service credits (not money)._\n"
                    response += "_Money moves outside. Ease lives inside._"
                    
                    return response
                elif resp.status_code == 502:
                    return f"💎 **ZEND UC Balance**\n\n🪙 **0.00 UC** (new account)\n\n_Start Zending to earn UC!_"
                else:
                    return "❌ Failed to fetch balance"
            except httpx.ConnectError:
                return "❌ Zend Wallet service is not available. Please try again later."
            except Exception as e:
                logger.error(f"Balance query error: {e}")
                return f"❌ Error fetching balance: {str(e)}"
        
        # ========== SEND UC ==========
        
        if ("send" in msg_lower or "zend" in msg_lower) and not "status" in msg_lower:
            # Check if this looks like a send command (has amount and recipient)
            amount = self.extract_amount(message)
            recipient, recipient_type = self.extract_recipient(message)
            
            if amount and (recipient or recipient_type != "unknown"):
                if not recipient:
                    return "❌ Please specify a recipient. Example: 'Send $50 to @alice' or 'Zend 100 UC to bob@email.com'"
                
                note = self.extract_description(message)
                
                try:
                    # Determine if direct send or invite
                    payload = {
                        "from_member_id": user_id,
                        "amount_uc": amount,
                        "note": note or f"Zend from {user_id}",
                        "confirm": True,
                    }
                    
                    if recipient_type == "member":
                        payload["to_member_id"] = recipient
                    else:
                        payload["invite_contact"] = recipient
                    
                    resp = await self.client.post(
                        f"{ZEND_WALLET_URL}/api/zend/send",
                        json=payload,
                        headers=headers,
                        timeout=15.0
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("success"):
                            if data.get("kind") == "invite":
                                return (
                                    f"✅ **Zend Sent!**\n\n"
                                    f"💰 Amount: {amount:.2f} UC\n"
                                    f"📧 To: {recipient}\n"
                                    f"🎁 Invite Code: `{data.get('invite_code')}`\n\n"
                                    f"Share the invite code with {recipient} to claim!\n\n"
                                    f"_Zend to Ascend_ ✨"
                                )
                            else:
                                return (
                                    f"✅ **Zend Sent!**\n\n"
                                    f"💰 Amount: {amount:.2f} UC\n"
                                    f"👤 To: @{recipient}\n\n"
                                    f"_Zend to Ascend_ ✨"
                                )
                        else:
                            return f"⚠️ Send requires confirmation: {data.get('message')}"
                    else:
                        error = resp.json().get("detail", "Unknown error")
                        return f"❌ Send failed: {error}"
                except httpx.ConnectError:
                    return "❌ Zend Wallet service is not available. Please try again later."
                except Exception as e:
                    logger.error(f"Send UC error: {e}")
                    return f"❌ Error sending UC: {str(e)}"
        
        # ========== PAYMENT STATUS ==========
        
        if "status" in msg_lower or ("check" in msg_lower and "payment" in msg_lower):
            # Extract code from message
            code_match = re.search(r'\b([a-zA-Z0-9_\-]{6,})\b', message)
            
            if not code_match:
                return "❌ Please provide a ZendLink code. Example: 'Status abc123'"
            
            code = code_match.group(1)
            
            try:
                resp = await self.client.get(
                    f"{ZEND_PAYMENTS_URL}/api/links/{code}",
                    headers=headers,
                    timeout=10.0
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "unknown")
                    amount = data.get("amount", 0)
                    
                    emoji_map = {
                        "pending": "⏳",
                        "settled": "✅",
                        "expired": "⌛",
                        "cancelled": "❌",
                        "failed": "❌",
                    }
                    emoji = emoji_map.get(status, "❓")
                    
                    return (
                        f"{emoji} **Payment Status: {status.upper()}**\n\n"
                        f"💰 Amount: ${amount:.2f}\n"
                        f"🏪 Recipient: {data.get('recipient_id', 'unknown')}\n"
                        f"🔗 Code: `{code}`\n"
                        f"⏰ Expires: {data.get('expires_at', 'N/A')[:19]}"
                    )
                elif resp.status_code == 404:
                    return f"❌ Payment link `{code}` not found or expired."
                else:
                    return "❌ Failed to fetch payment status"
            except httpx.ConnectError:
                return "❌ Zend Payments service is not available. Please try again later."
            except Exception as e:
                logger.error(f"Status query error: {e}")
                return f"❌ Error fetching status: {str(e)}"
        
        # ========== PAYMENT LINK ==========
        
        if ("link" in msg_lower or "request" in msg_lower) and ("payment" in msg_lower or "money" in msg_lower):
            amount = self.extract_amount(message)
            if not amount:
                return "❌ Please specify an amount. Example: 'Create payment link for $100'"
            
            note = self.extract_description(message)
            
            try:
                resp = await self.client.post(
                    f"{ZEND_PAYMENTS_URL}/api/intents",
                    json={
                        "recipient_id": user_id,
                        "amount": amount,
                        "currency": "USD",
                        "rail_policy": "stripe_first",
                        "note": note or "Payment request",
                        "expires_in_minutes": 30,
                    },
                    headers=headers,
                    timeout=10.0
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    return (
                        f"✅ **Payment Link Created!**\n\n"
                        f"💰 Amount: ${amount:.2f}\n"
                        f"🔗 **Link:** {data.get('zend_link')}\n\n"
                        f"Share this link to receive payment.\n"
                        f"⏰ Expires in 30 minutes\n\n"
                        f"_Zend to Ascend_ ✨"
                    )
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Link creation failed: {error}"
            except httpx.ConnectError:
                return "❌ Zend Payments service is not available. Please try again later."
            except Exception as e:
                logger.error(f"Payment link error: {e}")
                return f"❌ Error creating payment link: {str(e)}"
        
        # ========== HELP ==========
        
        if "zend" in msg_lower and ("help" in msg_lower or "how" in msg_lower or "what" in msg_lower):
            return (
                "💎 **Zend Money Commands**\n\n"
                "**Create Invoice (POS):**\n"
                "  • `Invoice $23.50 for 2 lattes`\n"
                "  • `Create invoice for $100`\n\n"
                "**Check Balance:**\n"
                "  • `My UC balance`\n"
                "  • `Balance`\n\n"
                "**Send UC:**\n"
                "  • `Send $50 to @alice`\n"
                "  • `Zend 100 UC to bob@email.com`\n\n"
                "**Payment Status:**\n"
                "  • `Status abc123`\n"
                "  • `Check payment xyz789`\n\n"
                "**Payment Link:**\n"
                "  • `Create payment link for $100`\n\n"
                "_Money moves outside. Ease lives inside._\n"
                "_Zend to Ascend_ ✨"
            )
        
        # No Zend command matched
        return None


# Singleton instance
_zend_commands: Optional[ZendCommands] = None


def get_zend_commands() -> ZendCommands:
    """Get singleton Zend commands instance."""
    global _zend_commands
    if _zend_commands is None:
        _zend_commands = ZendCommands()
    return _zend_commands




