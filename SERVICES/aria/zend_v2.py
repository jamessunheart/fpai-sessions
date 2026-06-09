"""
ARIA ZEND INTEGRATION v2.0
===========================

Connects Aria to the full ZEND ecosystem:
- UC wallet operations (balance, send, invite, claim)
- TON wallet integration (USDT balance, transfers)
- Entity management (trusts, churches, LLCs)
- P2P marketplace (cash out, buy UC)
- Unified balance view

Services:
- zend-wallet (8580): UC operations
- zend-ton (8583): TON/USDT operations
- zend-marketplace (8584): P2P exchange
"""

import os
import re
import logging
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aria_zend")

# Configuration
ZEND_WALLET_URL = os.getenv("ZEND_WALLET_URL", "http://198.54.123.234:8580")
ZEND_TON_URL = os.getenv("ZEND_TON_URL", "http://198.54.123.234:8583")
ZEND_MARKETPLACE_URL = os.getenv("ZEND_MARKETPLACE_URL", "http://198.54.123.234:8584")
ZEND_ADMIN_KEY = os.getenv("ZEND_ADMIN_KEY", "zend_dev_key_change_me")

# Primary user
JAMES_MEMBER_ID = "james"


# =============================================================================
# ZEND WALLET CLIENT
# =============================================================================


class ZendWallet:
    """UC wallet operations."""

    def __init__(self, base_url: str = ZEND_WALLET_URL, admin_key: str = ZEND_ADMIN_KEY):
        self.base_url = base_url.rstrip("/")
        self.admin_key = admin_key

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.admin_key:
            headers["X-Zend-Key"] = self.admin_key
            headers["X-Zend-Admin-Key"] = self.admin_key
        return headers

    async def get_balance(self, member_id: str = JAMES_MEMBER_ID) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/zend/wallet/{member_id}",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return {"error": str(e)}

    async def get_unified_balance(self, member_id: str = JAMES_MEMBER_ID) -> Dict:
        """Get unified balance including entities."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/zend/wallet/{member_id}/unified",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Unified balance failed: {e}")
            return {"error": str(e)}

    async def draft_send(self, member_id: str, prompt: str) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/zend/draft-send",
                    headers=self._headers(),
                    json={"member_id": member_id, "prompt": prompt}
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Draft send failed: {e}")
            return {"error": str(e)}

    async def send_uc(
        self,
        from_member_id: str,
        amount_uc: float,
        to_member_id: Optional[str] = None,
        invite_contact: Optional[str] = None,
        note: str = "",
        confirm: bool = True
    ) -> Dict:
        payload = {
            "from_member_id": from_member_id,
            "amount_uc": amount_uc,
            "note": note,
            "confirm": confirm
        }
        if to_member_id:
            payload["to_member_id"] = to_member_id
        elif invite_contact:
            payload["invite_contact"] = invite_contact
        else:
            return {"error": "Must provide to_member_id or invite_contact"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/zend/send",
                    headers=self._headers(),
                    json=payload
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Send UC failed: {e}")
            return {"error": str(e)}

    async def claim_invite(self, invite_code: str, claimer_member_id: str) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/zend/invites/claim",
                    headers=self._headers(),
                    json={
                        "invite_code": invite_code,
                        "claimer_member_id": claimer_member_id,
                        "confirm": True
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Claim invite failed: {e}")
            return {"error": str(e)}

    # Entity operations
    async def get_member_entities(self, member_id: str) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/zend/member/{member_id}/entities",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"entities": [], "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"entities": [], "error": str(e)}

    async def get_entity(self, entity_id: str) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/zend/entities/{entity_id}",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}

    async def distribute_from_entity(
        self,
        entity_id: str,
        distributions: List[Dict[str, Any]],
        note: str = ""
    ) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/zend/entities/{entity_id}/distribute",
                    headers=self._headers(),
                    json={"distributions": distributions, "note": note}
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# TON CLIENT
# =============================================================================


class TonClient:
    """TON wallet operations."""

    def __init__(self, base_url: str = ZEND_TON_URL):
        self.base_url = base_url.rstrip("/")

    async def get_wallet(self, member_id: str) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/ton/wallet/{member_id}")
                if resp.status_code == 200:
                    return resp.json()
                return {"connected": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    async def create_transfer(
        self,
        from_member_id: str,
        to_address: str,
        amount_usdt: float,
        comment: str = ""
    ) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/ton/transfer",
                    json={
                        "from_member_id": from_member_id,
                        "to_address": to_address,
                        "amount_usdt": amount_usdt,
                        "comment": comment
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# MARKETPLACE CLIENT
# =============================================================================


class MarketplaceClient:
    """P2P marketplace operations."""

    def __init__(self, base_url: str = ZEND_MARKETPLACE_URL):
        self.base_url = base_url.rstrip("/")

    async def create_sell_order(
        self,
        member_id: str,
        amount_uc: float,
        ton_wallet_address: Optional[str] = None
    ) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/marketplace/orders",
                    json={
                        "order_type": "sell_uc",
                        "member_id": member_id,
                        "amount_uc": amount_uc,
                        "accepted_rails": ["ton_usdt"],
                        "ton_wallet_address": ton_wallet_address
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}

    async def create_buy_order(
        self,
        member_id: str,
        amount_uc: float,
        entity_id: Optional[str] = None
    ) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/marketplace/orders",
                    json={
                        "order_type": "buy_uc",
                        "member_id": member_id,
                        "entity_id": entity_id,
                        "amount_uc": amount_uc,
                        "accepted_rails": ["ton_usdt"]
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_stats(self) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/marketplace/stats")
                if resp.status_code == 200:
                    return resp.json()
                return {}
        except Exception:
            return {}


# =============================================================================
# SINGLETONS
# =============================================================================

_zend: Optional[ZendWallet] = None
_ton: Optional[TonClient] = None
_marketplace: Optional[MarketplaceClient] = None


def get_zend() -> ZendWallet:
    global _zend
    if _zend is None:
        _zend = ZendWallet()
    return _zend


def get_ton() -> TonClient:
    global _ton
    if _ton is None:
        _ton = TonClient()
    return _ton


def get_marketplace() -> MarketplaceClient:
    global _marketplace
    if _marketplace is None:
        _marketplace = MarketplaceClient()
    return _marketplace


# =============================================================================
# ARIA TOOL FUNCTIONS
# =============================================================================


async def aria_unified_balance(member_id: str = JAMES_MEMBER_ID) -> str:
    """Get unified balance - UC + entities + TON."""
    zend = get_zend()
    ton = get_ton()

    # Get unified UC balance
    unified = await zend.get_unified_balance(member_id)
    if "error" in unified:
        return f"❌ Balance error: {unified['error']}"

    # Get TON balance
    ton_wallet = await ton.get_wallet(member_id)

    response = "💰 **Your Balances**\n\n"

    # Personal UC
    response += "**INTERNAL (UC)**\n"
    response += f"├─ 👤 Personal: {unified.get('uc_balance', 0):.2f} UC\n"

    # Entity contexts
    entities = unified.get("entity_contexts", [])
    for e in entities:
        role_icon = "👑" if e.get("role") == "admin" else "👤"
        response += f"├─ {role_icon} {e.get('name', 'Entity')}: {e.get('uc_balance', 0):.2f} UC ({e.get('role')})\n"

    total_uc = unified.get("uc_balance", 0) + sum(e.get("uc_balance", 0) for e in entities if e.get("role") == "admin")
    response += f"└─ **Total UC:** {total_uc:.2f} UC\n\n"

    # TON wallet
    if ton_wallet.get("connected"):
        response += "**EXTERNAL (TON Wallet)**\n"
        response += f"├─ 💵 USDT: ${ton_wallet.get('usdt_balance', 0):.2f}\n"
        response += f"├─ 💎 TON: {ton_wallet.get('ton_balance', 0):.2f}\n"
        response += f"└─ 📈 Earning: {ton_wallet.get('usdt_yield_apy', 2.86):.2f}% APY\n\n"
    else:
        response += "**EXTERNAL (TON Wallet):** Not connected\n\n"

    # Total value
    ton_value = ton_wallet.get("usdt_balance", 0) + ton_wallet.get("ton_balance", 0) * 5.5  # Approximate TON price
    total_value = total_uc + ton_value
    response += f"**💫 Combined Value:** ~${total_value:,.2f}\n"

    return response


async def aria_check_balance(member_id: str = JAMES_MEMBER_ID) -> str:
    """Simple UC balance check."""
    zend = get_zend()
    result = await zend.get_balance(member_id)

    if "error" in result:
        return f"❌ Couldn't check balance: {result['error']}"

    uc = result.get("uc_balance", 0)
    unlocked = result.get("unlocked", [])

    response = f"💰 **Your UC Balance:** {uc:.2f} UC\n\n"

    if unlocked:
        response += "🔓 **Unlocked Features:**\n"
        for u in unlocked:
            response += f"  • {u}\n"

    return response


async def aria_send_uc(prompt: str, member_id: str = JAMES_MEMBER_ID) -> Dict:
    """Send UC using natural language."""
    zend = get_zend()

    draft = await zend.draft_send(member_id, prompt)

    if "error" in draft:
        return {
            "success": False,
            "message": f"❌ Couldn't parse your request: {draft['error']}",
            "needs_confirmation": False
        }

    recipient = draft.get("recipient")
    amount = draft.get("amount_uc", 0)
    note = draft.get("note", "")
    recipient_type = draft.get("recipient_type", "unknown")
    risk_flags = draft.get("risk_flags", [])

    if not recipient or amount <= 0:
        return {
            "success": False,
            "message": "❌ I couldn't understand the recipient or amount. Try: 'Send 50 UC to @bob'",
            "needs_confirmation": False
        }

    risk_warning = ""
    if risk_flags:
        risk_warning = f"\n⚠️ Flags: {', '.join(risk_flags)}"

    return {
        "success": True,
        "needs_confirmation": True,
        "draft": draft,
        "message": f"""📤 **UC Transfer Draft**

**To:** {recipient} ({recipient_type})
**Amount:** {amount:.2f} UC
**Note:** {note or '(none)'}{risk_warning}

Reply "confirm" to send, or "cancel" to abort."""
    }


async def aria_confirm_send(draft: Dict, member_id: str = JAMES_MEMBER_ID) -> str:
    """Execute a confirmed UC send."""
    zend = get_zend()

    recipient = draft.get("recipient")
    amount = draft.get("amount_uc", 0)
    note = draft.get("note", "")
    recipient_type = draft.get("recipient_type", "unknown")

    if recipient_type == "member":
        result = await zend.send_uc(
            from_member_id=member_id,
            to_member_id=recipient.lstrip("@"),
            amount_uc=amount,
            note=note,
            confirm=True
        )
    else:
        result = await zend.send_uc(
            from_member_id=member_id,
            invite_contact=recipient,
            amount_uc=amount,
            note=note,
            confirm=True
        )

    if result.get("success"):
        if result.get("kind") == "invite":
            invite_code = result.get("invite_code", "")
            return f"""✅ **UC Sent!**

**{amount:.2f} UC** escrowed for {recipient}

📬 Share this invite code: `{invite_code}`

They can claim it once they sign up!"""
        else:
            return f"""✅ **UC Sent!**

**{amount:.2f} UC** transferred to {recipient}

Transaction complete."""
    else:
        return f"❌ Transfer failed: {result.get('message', result.get('error', 'Unknown error'))}"


async def aria_claim_invite(invite_code: str, claimer_id: str) -> str:
    """Claim an invite code."""
    zend = get_zend()
    result = await zend.claim_invite(invite_code, claimer_id)

    if result.get("success"):
        amount = result.get("amount_uc", 0)
        return f"✅ **Invite Claimed!** {amount:.2f} UC credited to your wallet."
    else:
        return f"❌ Couldn't claim invite: {result.get('error', 'Unknown error')}"


async def aria_cash_out(amount_uc: float, member_id: str = JAMES_MEMBER_ID) -> str:
    """Cash out UC via P2P marketplace."""
    zend = get_zend()
    ton = get_ton()
    marketplace = get_marketplace()

    # Check UC balance
    balance = await zend.get_balance(member_id)
    uc_balance = balance.get("uc_balance", 0)
    if uc_balance < amount_uc:
        return f"❌ Insufficient balance. You have {uc_balance:.2f} UC, trying to cash out {amount_uc:.2f} UC."

    # Check TON wallet
    ton_wallet = await ton.get_wallet(member_id)
    if not ton_wallet.get("connected"):
        return """❌ No TON wallet connected.

To cash out, you need a TON wallet to receive USDT.
Say "connect ton wallet" to get started."""

    # Create sell order
    result = await marketplace.create_sell_order(
        member_id=member_id,
        amount_uc=amount_uc,
        ton_wallet_address=ton_wallet.get("ton_address")
    )

    if "error" in result:
        return f"❌ Cash out failed: {result['error']}"

    if result.get("status") == "matched":
        return f"""⚡ **Instant Match!**

Your {amount_uc:.2f} UC has been matched with a liquidity provider.

They will send **${amount_uc:.2f} USDT** to your TON wallet.

You'll be notified when payment is received."""
    else:
        return f"""📋 **Cash Out Order Created**

**Amount:** {amount_uc:.2f} UC
**Rate:** 1 UC = $1.00 USDT
**You'll receive:** ~${amount_uc:.2f} USDT

Your order is in the marketplace. You'll be matched with a buyer soon.
Order ID: `{result.get('order_id')}`"""


async def aria_entity_balance(entity_name: str, member_id: str = JAMES_MEMBER_ID) -> str:
    """Get balance for an entity the member admins."""
    zend = get_zend()

    entities = await zend.get_member_entities(member_id)
    entity_list = entities.get("entities", [])

    # Find matching entity
    entity_name_lower = entity_name.lower()
    matched = None
    for e in entity_list:
        if entity_name_lower in e.get("legal_name", "").lower() or entity_name_lower in e.get("entity_id", "").lower():
            matched = e
            break

    if not matched:
        available = ", ".join(e.get("legal_name", "Unknown") for e in entity_list) or "None"
        return f"❌ Entity '{entity_name}' not found. Your entities: {available}"

    entity_details = await zend.get_entity(matched["entity_id"])
    if "error" in entity_details:
        return f"❌ Error getting entity: {entity_details['error']}"

    etype = entity_details.get("entity_type", "unknown")
    type_emoji = {"trust": "🏛️", "church": "⛪", "llc": "🏢", "nonprofit": "💚"}.get(etype, "📋")

    return f"""{type_emoji} **{entity_details.get('legal_name')}**

**Type:** {etype.title()}
**Balance:** {entity_details.get('uc_balance', 0):.2f} UC
**Daily Distribute Limit:** {entity_details.get('daily_distribute_limit_uc', 0):,.0f} UC

**Admins:** {', '.join(entity_details.get('admins', []))}
**Beneficiaries:** {', '.join(entity_details.get('beneficiaries', [])) or 'None'}"""


async def aria_distribute(
    entity_name: str,
    distributions: List[Dict[str, Any]],
    member_id: str = JAMES_MEMBER_ID
) -> str:
    """Distribute UC from an entity."""
    zend = get_zend()

    entities = await zend.get_member_entities(member_id)
    entity_list = entities.get("entities", [])

    # Find matching entity
    entity_name_lower = entity_name.lower()
    matched = None
    for e in entity_list:
        if entity_name_lower in e.get("legal_name", "").lower():
            matched = e
            break

    if not matched:
        return f"❌ Entity '{entity_name}' not found."

    if matched.get("role") != "admin":
        return f"❌ You don't have admin access to {matched.get('legal_name')}."

    result = await zend.distribute_from_entity(
        entity_id=matched["entity_id"],
        distributions=distributions,
        note=f"Distribution via Aria"
    )

    if "error" in result:
        return f"❌ Distribution failed: {result['error']}"

    if result.get("success"):
        return f"""✅ **Distribution Complete!**

**From:** {matched.get('legal_name')}
**Recipients:** {result.get('distributed_count')}
**Total:** {result.get('total_uc', 0):.2f} UC
**Treasury After:** {result.get('treasury_after', 0):.2f} UC"""
    else:
        return f"⚠️ Partial distribution: {result.get('message')}"


# =============================================================================
# INTENT DETECTION
# =============================================================================


def detect_zend_intent(message: str) -> Optional[str]:
    """Detect ZEND-related intents from message."""
    msg_lower = message.lower()

    # Balance checks
    if any(k in msg_lower for k in ["balance", "wallet", "how much", "uc balance", "my uc", "check uc", "balances"]):
        if any(k in msg_lower for k in ["unified", "all", "everything", "full"]):
            return "unified_balance"
        return "balance"

    # Send UC
    if any(k in msg_lower for k in ["send", "zend", "transfer", "pay", "give uc", "send uc"]):
        if "$" in message or "usdt" in msg_lower or "dollars" in msg_lower:
            return "send_usdt"
        return "send_uc"

    # Cash out
    if any(k in msg_lower for k in ["cash out", "cashout", "convert", "sell uc", "withdraw"]):
        return "cash_out"

    # Claim invite
    if any(k in msg_lower for k in ["claim", "redeem", "use invite", "use code"]):
        return "claim"

    # Entity operations
    if any(k in msg_lower for k in ["distribute", "distribution"]):
        return "distribute"
    if any(k in msg_lower for k in ["trust", "church", "llc", "entity"]) and "balance" in msg_lower:
        return "entity_balance"

    # TON wallet
    if any(k in msg_lower for k in ["connect ton", "ton wallet", "link wallet"]):
        return "connect_ton"

    return None


async def process_zend_command(message: str, member_id: str = JAMES_MEMBER_ID) -> Optional[str]:
    """Process a ZEND-related command."""
    intent = detect_zend_intent(message)

    if intent == "unified_balance":
        return await aria_unified_balance(member_id)

    elif intent == "balance":
        return await aria_check_balance(member_id)

    elif intent == "send_uc":
        result = await aria_send_uc(message, member_id)
        return result.get("message")

    elif intent == "claim":
        code_match = re.search(r"zend_[a-zA-Z0-9_-]+", message)
        if code_match:
            return await aria_claim_invite(code_match.group(0), member_id)
        return "❌ Please include the invite code (e.g., 'claim zend_abc123')"

    elif intent == "cash_out":
        amount_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if amount_match:
            amount = float(amount_match.group(1))
            return await aria_cash_out(amount, member_id)
        return "❌ Please specify amount: 'cash out 100 UC'"

    elif intent == "entity_balance":
        for name in ["trust", "church", "sacred flow", "sunheart", "holdings"]:
            if name in message.lower():
                return await aria_entity_balance(name, member_id)
        return "❌ Which entity? Try: 'trust balance' or 'church balance'"

    elif intent == "distribute":
        return """📋 **Distribution**

To distribute from an entity, tell me:
- Which entity (trust, church, etc.)
- Recipients and amounts

Example: "Distribute 500 UC from Sacred Flow: 100 to @maria, 100 to @carlos, 100 to @amy"

Or say "help distribute" for more options."""

    elif intent == "connect_ton":
        return """💎 **Connect TON Wallet**

To connect your TON wallet:
1. Open Telegram's built-in Wallet
2. Go to Settings → TON Connect
3. Or use the TON Wallet mini-app

Your wallet will be automatically linked when you make your first transaction.

💡 Tip: Make sure you have some TON for gas fees."""

    elif intent == "send_usdt":
        return """💵 **Send USDT**

To send real money (USDT), I'll generate a payment link for you.

Please specify:
- Recipient's TON address or @username
- Amount in USDT

Example: "Send $50 USDT to @sarah"

Note: USDT transfers happen on the TON blockchain. You'll need a connected TON wallet."""

    return None


# =============================================================================
# ZEND HELP
# =============================================================================


def get_zend_help() -> str:
    """Return Zend help text."""
    return """💫 **ZEND Commands**

**Balance:**
• "my balance" - Quick UC balance
• "all balances" - UC + entities + TON

**Send UC:**
• "zend 50 UC to @bob"
• "send 100 to maria@email.com"

**Cash Out:**
• "cash out 100 UC" - Convert to USDT

**Entities:**
• "trust balance" - Check entity balance
• "distribute from church..." - Distribute UC

**TON:**
• "connect ton wallet"
• "send $50 to @user" - USDT transfer

**Invites:**
• "claim zend_abc123" - Claim invite code

*1 UC = $1 USD (fixed)*
*Money moves outside. Ease lives inside.*"""


if __name__ == "__main__":
    import asyncio

    async def test():
        print(await aria_unified_balance("james"))

    asyncio.run(test())




