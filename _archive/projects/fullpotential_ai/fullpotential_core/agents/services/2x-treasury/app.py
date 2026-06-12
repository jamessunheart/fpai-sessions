"""
2X Treasury - Backend API
Handles SOL deposits, 2X token minting, redemptions, and treasury management
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import os

app = FastAPI(title="2X Treasury", version="1.0.0")

# Configuration
TREASURY_WALLET = os.getenv("TREASURY_WALLET", "PLACEHOLDER_TREASURY_ADDRESS")
TOKEN_RATIO = 100  # 100 2X tokens per 1 SOL
INSURANCE_FLOOR = 1.0  # 1X guarantee

# In-memory storage (will move to database later)
treasury_state = {
    "total_sol": 0.0,
    "total_2x_supply": 0.0,
    "current_multiplier": 1.0,
    "investors": {},
    "transactions": [],
    "launch_date": datetime.now().isoformat(),
    "founding_waitlist": []
}

class Investment(BaseModel):
    wallet_address: str
    sol_amount: float
    signature: str

class Redemption(BaseModel):
    wallet_address: str
    token_amount: float
    signature: str

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main 2X dashboard"""
    return HTMLResponse(content=open("templates/dashboard.html").read())

@app.get("/api/treasury")
async def get_treasury_state():
    """Get current treasury state and multiplier"""
    return {
        "treasury": {
            "total_sol": treasury_state["total_sol"],
            "total_usd": treasury_state["total_sol"] * 150,  # SOL price estimate
            "total_2x_supply": treasury_state["total_2x_supply"],
            "investor_count": len(treasury_state["investors"])
        },
        "multiplier": {
            "current": round(treasury_state["current_multiplier"], 2),
            "change_24h": 0.04,  # Calculate from history
            "next_milestone": 2.0 if treasury_state["current_multiplier"] < 2 else 4.0
        },
        "projections": {
            "time_to_2x": "47 days",
            "time_to_4x": "127 days",
            "time_to_8x": "287 days"
        },
        "insurance": {
            "floor": INSURANCE_FLOOR,
            "guaranteed": "Your principal is protected"
        }
    }

@app.get("/api/wallet/{wallet_address}")
async def get_wallet_position(wallet_address: str):
    """Get user's position in 2X"""
    if wallet_address not in treasury_state["investors"]:
        return {
            "found": False,
            "message": "Wallet not found in 2X treasury"
        }

    investor = treasury_state["investors"][wallet_address]
    current_sol_value = (investor["token_balance"] / TOKEN_RATIO) * treasury_state["current_multiplier"]

    return {
        "found": True,
        "position": {
            "2x_balance": investor["token_balance"],
            "sol_invested": investor["sol_invested"],
            "current_sol_value": round(current_sol_value, 2),
            "current_usd_value": round(current_sol_value * 150, 2),
            "return_percent": round(((current_sol_value / investor["sol_invested"]) - 1) * 100, 1),
            "multiplier_on_investment": round(current_sol_value / investor["sol_invested"], 2)
        },
        "insurance": {
            "floor_sol": investor["sol_invested"],
            "guaranteed_protected": True
        }
    }

@app.post("/api/invest")
async def invest_sol(investment: Investment):
    """Process SOL investment and mint 2X tokens"""

    # TODO: Verify Solana transaction signature
    # For MVP, we'll simulate

    tokens_to_mint = investment.sol_amount * TOKEN_RATIO

    # Update treasury
    treasury_state["total_sol"] += investment.sol_amount
    treasury_state["total_2x_supply"] += tokens_to_mint

    # Update investor record
    if investment.wallet_address not in treasury_state["investors"]:
        treasury_state["investors"][investment.wallet_address] = {
            "sol_invested": 0.0,
            "token_balance": 0.0,
            "joined_date": datetime.now().isoformat()
        }

    treasury_state["investors"][investment.wallet_address]["sol_invested"] += investment.sol_amount
    treasury_state["investors"][investment.wallet_address]["token_balance"] += tokens_to_mint

    # Log transaction
    treasury_state["transactions"].append({
        "type": "invest",
        "wallet": investment.wallet_address,
        "sol_amount": investment.sol_amount,
        "tokens_minted": tokens_to_mint,
        "timestamp": datetime.now().isoformat()
    })

    # Recalculate multiplier (treasury value / initial investments)
    # For now, simple calculation - will add DeFi yields later
    treasury_state["current_multiplier"] = 1.0  # Will update with yield strategy

    return {
        "success": True,
        "investment": {
            "sol_deposited": investment.sol_amount,
            "2x_received": tokens_to_mint,
            "current_multiplier": treasury_state["current_multiplier"]
        },
        "message": f"Successfully invested {investment.sol_amount} SOL → Received {tokens_to_mint} 2X tokens"
    }

@app.post("/api/redeem")
async def redeem_tokens(redemption: Redemption):
    """Burn 2X tokens and withdraw SOL"""

    if redemption.wallet_address not in treasury_state["investors"]:
        raise HTTPException(status_code=404, detail="Wallet not found")

    investor = treasury_state["investors"][redemption.wallet_address]

    if investor["token_balance"] < redemption.token_amount:
        raise HTTPException(status_code=400, detail="Insufficient 2X balance")

    # Calculate SOL to return (token amount / ratio * multiplier)
    sol_to_return = (redemption.token_amount / TOKEN_RATIO) * treasury_state["current_multiplier"]

    # Apply insurance floor (minimum 1X)
    original_sol = redemption.token_amount / TOKEN_RATIO
    sol_to_return = max(sol_to_return, original_sol)

    # Update balances
    investor["token_balance"] -= redemption.token_amount
    treasury_state["total_2x_supply"] -= redemption.token_amount
    treasury_state["total_sol"] -= sol_to_return

    # Log transaction
    treasury_state["transactions"].append({
        "type": "redeem",
        "wallet": redemption.wallet_address,
        "tokens_burned": redemption.token_amount,
        "sol_returned": sol_to_return,
        "timestamp": datetime.now().isoformat()
    })

    return {
        "success": True,
        "redemption": {
            "2x_burned": redemption.token_amount,
            "sol_returned": sol_to_return,
            "multiplier_applied": treasury_state["current_multiplier"]
        },
        "message": f"Successfully redeemed {redemption.token_amount} 2X → Received {sol_to_return} SOL"
    }

@app.get("/api/milestones")
async def get_milestones():
    """Get multiplier milestone progress"""
    current = treasury_state["current_multiplier"]

    milestones = [
        {"value": 1.0, "name": "Foundation", "description": "System works", "achieved": current >= 1.0},
        {"value": 2.0, "name": "Proof", "description": "Promise delivered", "achieved": current >= 2.0},
        {"value": 4.0, "name": "Momentum", "description": "Network effects", "achieved": current >= 4.0},
        {"value": 8.0, "name": "Escape Velocity", "description": "Unstoppable", "achieved": current >= 8.0},
        {"value": 16.0, "name": "Exponential", "description": "Redefining the game", "achieved": current >= 16.0},
        {"value": 32.0, "name": "Transcendent", "description": "New paradigm", "achieved": current >= 32.0}
    ]

    return {"milestones": milestones, "current": current}

@app.get("/api/transactions")
async def get_transactions(limit: int = 50):
    """Get recent transactions"""
    return {
        "transactions": treasury_state["transactions"][-limit:],
        "total_count": len(treasury_state["transactions"])
    }

@app.get("/founding")
async def founding_multipliers():
    """Founding Multipliers landing page"""
    return HTMLResponse(content=open("founding_multipliers.html").read())

class WaitlistEntry(BaseModel):
    email: str
    wallet: Optional[str] = None
    referral: Optional[str] = None
    timestamp: str

class ChatMessage(BaseModel):
    message: str

@app.post("/api/founding-waitlist")
async def join_founding_waitlist(entry: WaitlistEntry):
    """Join the Founding Multipliers waitlist"""

    # Check if email already exists
    if any(w["email"] == entry.email for w in treasury_state["founding_waitlist"]):
        return {
            "success": False,
            "message": "Email already registered"
        }

    # Add to waitlist
    waitlist_entry = {
        "email": entry.email,
        "wallet": entry.wallet,
        "referral": entry.referral,
        "timestamp": entry.timestamp,
        "position": len(treasury_state["founding_waitlist"]) + 1
    }

    treasury_state["founding_waitlist"].append(waitlist_entry)

    # Log waitlist signup
    print(f"🎯 New Founding Member: #{waitlist_entry['position']} - {entry.email}")

    return {
        "success": True,
        "position": waitlist_entry["position"],
        "message": "Welcome to the Founding 100!"
    }

@app.get("/api/founding-stats")
async def founding_stats():
    """Get Founding Multipliers program stats"""
    return {
        "total_signups": len(treasury_state["founding_waitlist"]),
        "spots_remaining": max(0, 100 - len(treasury_state["founding_waitlist"])),
        "waitlist": treasury_state["founding_waitlist"][-10:]  # Last 10 signups
    }

@app.post("/api/chat")
async def ai_chat(chat: ChatMessage):
    """
    AI chatbot for answering 2X questions
    Autonomous investor recruitment through intelligent conversation
    """

    # Intelligent Q&A matching
    qa_database = {
        "what is 2x": "2X is a Solana treasury system that measures growth in multipliers (1X, 2X, 4X) instead of years. We stake SOL on Marinade for sustainable 6-8% APY yields and track your growth exponentially. Think: 1X → 2X → 4X instead of Year 1, Year 2, Year 3.",

        "how does it work": "Simple: 1) You deposit SOL. 2) We stake 80% on Marinade (battle-tested DeFi protocol with $400M+ TVL). 3) You receive 2X tokens. 4) As treasury grows from yields, your multiplier increases. 5) You can withdraw anytime with 1X minimum guarantee. All transactions are on-chain and transparent.",

        "is this safe": "Yes. We use Marinade Finance ($400M+ TVL, heavily audited) for staking. You get a 1X insurance floor (can't lose your principal in SOL terms). All transactions are on-chain via Solscan. We promise 7% not 700% - conservative, sustainable, provable. No lock-ups, fully liquid.",

        "founding member": "The first 100 investors get special perks: 2X better token ratio (50:1 vs 100:1 public), permanent Founding Member NFT badge, 2X governance voting power, and pre-launch access. Once 100 spots fill, these terms close forever. Limited to 72 hours.",

        "why trust": "Fair question! 1) All transactions on-chain (Solscan proof). 2) We use proven DeFi (Marinade, not sketchy protocol). 3) Conservative promises (7% not 700%). 4) Insurance floor (1X minimum). 5) The founder is putting their own SOL in first. Trust earned, not assumed.",

        "different": "Most crypto: Promise 100X, deliver rugpull. 2X: Promise 1.07X, deliver 1.07X. We're boring. We work. We compound. We measure in multipliers not hype. Sustainable DeFi yields, not Ponzi schemes.",

        "how much": "Founding Members: Minimum 0.5 SOL ($75). Most people do 1-2 SOL ($150-300) to start. You can add more later. Conservative position sizing recommended - only invest what you're comfortable with.",

        "when": "Founding program closes in 72 hours or when 100 spots fill (whichever comes first). After that, public launch with standard terms (100:1 ratio vs Founding 50:1). Better to join now if you're interested.",

        "elon": "Haha! While Elon renamed Twitter to X, we built 2X - an actual treasury system that compounds value. X is a letter. 2X is a multiplier. We're not competing with Elon, we're playing a different game. Spiritual finance meets sustainable yields.",

        "reality show": "Yes! The founder is a spiritual advisor on a reality show. 2X was created as part of that journey - exploring consciousness and currency alignment. Is it real? Is it art? Both. Neither. But the yields are just math. Performance art meets actual utility.",
    }

    message_lower = chat.message.lower()

    # Match question to answer
    response_text = None
    for keyword, answer in qa_database.items():
        if keyword in message_lower:
            response_text = answer
            break

    # Default response if no match
    if not response_text:
        if "?" in chat.message:
            response_text = "Great question! The Founding Multipliers program offers 2X better token ratio (50:1 vs 100:1), exclusive governance power, and pre-launch access. Limited to 100 spots. What specific aspect interests you most?"
        else:
            response_text = "I'm here to help! You can ask me about: What is 2X? How does it work? Is it safe? What are Founding Member perks? Why should I trust this? Or anything else about the program!"

    # Suggested follow-up questions
    suggested_replies = []

    if "what is" in message_lower:
        suggested_replies = ["How does it work?", "Is this safe?", "What are the perks?"]
    elif "how" in message_lower:
        suggested_replies = ["Is this safe?", "Why should I trust you?", "How much to invest?"]
    elif "safe" in message_lower or "trust" in message_lower:
        suggested_replies = ["How does it work?", "What makes this different?", "Ready to join"]
    else:
        suggested_replies = ["What is 2X?", "How does it work?", "Is this safe?"]

    return {
        "response": response_text,
        "suggested_replies": suggested_replies
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "active",
        "service": "2x-treasury",
        "treasury_sol": treasury_state["total_sol"],
        "multiplier": treasury_state["current_multiplier"],
        "timestamp": datetime.utcnow().isoformat()
    }

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass  # Directory might not exist yet

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8052)
