#!/usr/bin/env python3
"""
🤝 Contribution Routes - One-Click Sharing & Task System
Make it easier to help than to ignore

Session #6 (Catalyst) - Human Participation System
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
import urllib.parse
from datetime import datetime

from ..services.pot_service import POTService, CONTRIBUTION_REWARDS, EQUITY_REWARDS


router = APIRouter(prefix="/contribute", tags=["contributions"])
pot_service = POTService()


class ShareRequest(BaseModel):
    """One-click share request"""
    user_id: int
    platform: str  # "reddit", "linkedin", "email"
    recipient_email: Optional[str] = None  # For email sharing
    custom_message: Optional[str] = None  # Optional personalization


class TaskCompletionRequest(BaseModel):
    """Task completion submission"""
    user_id: int
    task_id: int
    submission: dict  # Task-specific data


def generate_share_content(user_id: int, platform: str) -> dict:
    """
    Generate pre-written content for sharing
    Based on user's experience (customize later with real testimonials)
    """
    base_content = {
        "reddit": {
            "title": "Found an AI that matches you with the perfect financial advisor",
            "body": """I was frustrated trying to find a financial advisor who actually understood tech compensation (RSUs, ISOs, tax optimization).

Generic advisors just didn't get it. Fee-only vs commission? Investment philosophy? Communication style? It was overwhelming.

Then I found I MATCH - an AI that analyzes 100+ advisors and finds your perfect fit based on:
• Your specific needs (not generic advice)
• Values alignment (fee-only, fiduciary, etc.)
• Communication style (how you like to work)
• Specialization (tech comp, real estate, etc.)

**Free for customers.** Advisors only pay if you engage.

Just got matched and it's honestly impressive. The fit is 94%.

If you're looking for a financial advisor, check it out: http://198.54.123.234:8401/

(They're in beta so spots are limited)"""
        },
        "linkedin": {
            "text": """Just used I MATCH to find a financial advisor and I'm impressed 🎯

The AI analyzed 100+ advisors and found a 94% compatibility match based on:
✅ My specific needs (RSUs, tax optimization)
✅ Values alignment (fee-only, fiduciary)
✅ Communication style
✅ Specialization

Free for customers. Actually works.

http://198.54.123.234:8401/

#FinancialPlanning #AIforGood #TechCompensation"""
        },
        "email": {
            "subject": "Found something useful - AI financial advisor matching",
            "body": """Hey,

I know we've talked about finding a good financial advisor. I just tried something that actually worked:

I MATCH - it's an AI that analyzes advisors and finds your perfect fit.

Instead of guessing or going with whoever your friend used, it matches based on:
- Your actual needs (RSUs, tax stuff, investment strategy)
- Values (fee-only vs commission, fiduciary status)
- How you like to communicate
- Their specialization

It's free for customers (advisors pay). I just got matched with a 94% fit.

Worth checking out if you're still looking: http://198.54.123.234:8401/

- [Your name]"""
        }
    }

    return base_content.get(platform, {})


@router.post("/share")
async def one_click_share(request: ShareRequest):
    """
    One-click sharing - generate shareable link or send directly
    Reward user with POT tokens immediately
    """
    # Generate content
    content = generate_share_content(request.user_id, request.platform)

    if not content:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {request.platform}")

    # Create shareable URLs
    if request.platform == "reddit":
        # Reddit share URL
        title = urllib.parse.quote(content["title"])
        body = urllib.parse.quote(content["body"])
        share_url = f"https://www.reddit.com/submit?title={title}&text={body}"

        # Award POT
        reward = pot_service.award_pot(
            user_id=request.user_id,
            amount=CONTRIBUTION_REWARDS["share_reddit"],
            source="share_reddit",
            description="Shared I MATCH on Reddit"
        )

        return {
            "success": True,
            "platform": "reddit",
            "share_url": share_url,
            "reward": reward,
            "message": "Click to share on Reddit! Your link is ready."
        }

    elif request.platform == "linkedin":
        # LinkedIn share URL
        url = "http://198.54.123.234:8401/"
        text = urllib.parse.quote(content["text"])
        share_url = f"https://www.linkedin.com/sharing/share-offsite/?url={url}&summary={text}"

        # Award POT
        reward = pot_service.award_pot(
            user_id=request.user_id,
            amount=CONTRIBUTION_REWARDS["share_linkedin"],
            source="share_linkedin",
            description="Shared I MATCH on LinkedIn"
        )

        return {
            "success": True,
            "platform": "linkedin",
            "share_url": share_url,
            "reward": reward,
            "message": "Click to share on LinkedIn! Your post is ready."
        }

    elif request.platform == "email":
        if not request.recipient_email:
            raise HTTPException(status_code=400, detail="recipient_email required for email sharing")

        # TODO: Integrate with email service to actually send
        # For now, return email content for user to send manually

        # Award POT
        reward = pot_service.award_pot(
            user_id=request.user_id,
            amount=CONTRIBUTION_REWARDS["share_email"],
            source="share_email",
            description=f"Shared I MATCH via email to {request.recipient_email}"
        )

        return {
            "success": True,
            "platform": "email",
            "email_content": content,
            "recipient": request.recipient_email,
            "reward": reward,
            "message": "Email content generated! Copy and send to earn your POT."
        }

    else:
        raise HTTPException(status_code=400, detail=f"Platform not supported: {request.platform}")


@router.get("/tasks")
async def get_available_tasks(user_id: int):
    """
    Get all available contribution tasks
    Personalized based on user's contribution history
    """
    user_stats = pot_service.get_user_stats(user_id)

    # Base tasks available to everyone
    tasks = [
        {
            "id": 1,
            "type": "share",
            "title": "Share on Reddit",
            "description": "Share I MATCH on Reddit (one click, pre-written post)",
            "estimated_minutes": 1,
            "reward_pot": CONTRIBUTION_REWARDS["share_reddit"],
            "reward_equity": 0,
            "difficulty": "easy"
        },
        {
            "id": 2,
            "type": "share",
            "title": "Share on LinkedIn",
            "description": "Share I MATCH on LinkedIn (one click, pre-written post)",
            "estimated_minutes": 1,
            "reward_pot": CONTRIBUTION_REWARDS["share_linkedin"],
            "reward_equity": 0,
            "difficulty": "easy"
        },
        {
            "id": 3,
            "type": "review",
            "title": "Write a Review",
            "description": "Share your I MATCH experience (3 questions, 5 minutes)",
            "estimated_minutes": 5,
            "reward_pot": CONTRIBUTION_REWARDS["write_review"],
            "reward_equity": EQUITY_REWARDS["write_review"],
            "difficulty": "easy"
        },
        {
            "id": 4,
            "type": "recruitment",
            "title": "Invite a Financial Advisor",
            "description": "Know a great advisor? Invite them to join I MATCH",
            "estimated_minutes": 10,
            "reward_pot": CONTRIBUTION_REWARDS["recruit_provider"],
            "reward_equity": EQUITY_REWARDS["recruit_provider"],
            "difficulty": "medium",
            "bonus": "10% of their lifetime revenue"
        },
        {
            "id": 5,
            "type": "recruitment",
            "title": "Refer a Friend",
            "description": "Know someone looking for a financial advisor?",
            "estimated_minutes": 5,
            "reward_pot": CONTRIBUTION_REWARDS["recruit_customer"],
            "reward_equity": 0,
            "difficulty": "easy"
        }
    ]

    # Add advanced tasks for active contributors
    if user_stats["contribution_count"] >= 10:
        tasks.extend([
            {
                "id": 6,
                "type": "support",
                "title": "Answer Questions",
                "description": "Help new users with their questions",
                "estimated_minutes": 10,
                "reward_pot": CONTRIBUTION_REWARDS["answer_question"],
                "reward_equity": 0,
                "difficulty": "medium"
            },
            {
                "id": 7,
                "type": "testing",
                "title": "Test New Features",
                "description": "Try our latest features and give feedback",
                "estimated_minutes": 15,
                "reward_pot": CONTRIBUTION_REWARDS["test_feature"],
                "reward_equity": 0,
                "difficulty": "medium"
            }
        ])

    return {
        "tasks": tasks,
        "user_stats": user_stats,
        "total_available": len(tasks)
    }


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: int, completion: TaskCompletionRequest):
    """
    Complete a contribution task
    Validate submission and reward contributor
    """
    if completion.task_id != task_id:
        raise HTTPException(status_code=400, detail="Task ID mismatch")

    # Task-specific validation and rewards
    if task_id == 3:  # Write review
        # Validate review submission
        required_fields = ["problem", "solution", "recommendation"]
        if not all(field in completion.submission for field in required_fields):
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {required_fields}"
            )

        # Award POT + equity
        pot_reward = pot_service.award_pot(
            user_id=completion.user_id,
            amount=CONTRIBUTION_REWARDS["write_review"],
            source="write_review",
            description="Wrote review of I MATCH experience"
        )

        equity_reward = pot_service.award_equity(
            user_id=completion.user_id,
            percentage=EQUITY_REWARDS["write_review"],
            source="contribution",
            vesting_years=4
        )

        # TODO: Save review for display on website

        return {
            "success": True,
            "task_id": task_id,
            "pot_reward": pot_reward,
            "equity_reward": equity_reward,
            "message": "Thank you! Your review helps others find perfect matches. 🎉"
        }

    elif task_id == 4:  # Recruit provider
        # Validate provider invitation
        if "advisor_email" not in completion.submission:
            raise HTTPException(status_code=400, detail="advisor_email required")

        # Award POT + equity
        pot_reward = pot_service.award_pot(
            user_id=completion.user_id,
            amount=CONTRIBUTION_REWARDS["recruit_provider"],
            source="recruit_provider",
            description=f"Invited advisor: {completion.submission['advisor_email']}"
        )

        equity_reward = pot_service.award_equity(
            user_id=completion.user_id,
            percentage=EQUITY_REWARDS["recruit_provider"],
            source="contribution",
            vesting_years=4
        )

        # TODO: Send invitation email to advisor
        # TODO: Track revenue share (10% lifetime)

        return {
            "success": True,
            "task_id": task_id,
            "pot_reward": pot_reward,
            "equity_reward": equity_reward,
            "bonus": "You'll earn 10% of this advisor's lifetime revenue!",
            "message": "Invitation sent! If they join, you'll be rewarded. 🤝"
        }

    elif task_id == 5:  # Refer friend
        if "friend_email" not in completion.submission:
            raise HTTPException(status_code=400, detail="friend_email required")

        # Award POT
        pot_reward = pot_service.award_pot(
            user_id=completion.user_id,
            amount=CONTRIBUTION_REWARDS["recruit_customer"],
            source="recruit_customer",
            description=f"Referred friend: {completion.submission['friend_email']}"
        )

        # TODO: Send referral email

        return {
            "success": True,
            "task_id": task_id,
            "pot_reward": pot_reward,
            "message": "Referral sent! Helping friends find perfect matches. 🌟"
        }

    else:
        raise HTTPException(status_code=400, detail=f"Task {task_id} not implemented yet")


@router.get("/stats")
async def get_contributor_stats(user_id: int):
    """
    Get comprehensive contributor statistics
    Shows impact, rewards, and progress
    """
    stats = pot_service.get_user_stats(user_id)

    # Add additional computed metrics
    stats["progress_to_next_tier"] = {
        "current_tier": stats["tier"],
        "next_tier_requirements": stats["next_tier"],
        "progress_percentage": min(100, (stats["contribution_count"] / (stats["next_tier"].get("contributions_needed", 1) + stats["contribution_count"])) * 100) if stats["next_tier"] else 100
    }

    # Estimated value
    pot_value_usd = stats["pot_balance"]  # 1 POT = $1 for platform services
    equity_value_usd = stats["equity_percentage"] * 100000  # Assume $100K current valuation (placeholder)

    stats["estimated_value"] = {
        "pot_usd": pot_value_usd,
        "equity_usd": equity_value_usd,
        "total_usd": pot_value_usd + equity_value_usd,
        "note": "Equity value is estimated based on current valuation"
    }

    return stats


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    """
    Get top contributors (gamification)
    """
    return {
        "leaderboard": pot_service.get_leaderboard(limit),
        "updated_at": datetime.utcnow().isoformat()
    }


@router.post("/convert-pot-to-equity")
async def convert_pot_to_equity(user_id: int, pot_amount: int):
    """
    Convert POT tokens to equity shares
    10,000 POT = 0.01% equity
    """
    result = pot_service.convert_pot_to_equity(user_id, pot_amount)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/join-movement", response_class=HTMLResponse)
async def join_movement_page():
    """
    Landing page for contributors
    Explains participation system and shows opportunities
    """
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Join the Movement - I MATCH</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        .hero {
            background: white;
            border-radius: 20px;
            padding: 60px 40px;
            margin-bottom: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { font-size: 3em; margin-bottom: 20px; color: #667eea; }
        .subtitle { font-size: 1.5em; color: #666; margin-bottom: 30px; }
        .cta-section {
            background: #f8f9fa;
            padding: 40px;
            border-radius: 15px;
            margin: 30px 0;
        }
        .task-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .task-card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .task-card:hover { transform: translateY(-5px); box-shadow: 0 8px 12px rgba(0,0,0,0.2); }
        .task-title { font-size: 1.5em; margin-bottom: 10px; color: #667eea; }
        .task-reward {
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            display: inline-block;
            margin-top: 15px;
            font-weight: bold;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 1.1em;
            transition: background 0.3s;
        }
        .btn:hover { background: #764ba2; }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>🌐 Join the Movement</h1>
            <p class="subtitle">Build paradise on Earth. Get rewarded with equity + tokens.</p>

            <p>We're creating a new economic system where everyone who helps build owns a piece of what we create.</p>

            <p><strong>Not a reward program. A new paradigm.</strong></p>
        </div>

        <div class="cta-section">
            <h2>💎 How It Works</h2>
            <ol style="font-size: 1.2em; margin-top: 20px;">
                <li style="margin: 15px 0;"><strong>Contribute</strong> - Share, review, recruit, or join the team</li>
                <li style="margin: 15px 0;"><strong>Earn POT tokens</strong> - Every contribution is rewarded</li>
                <li style="margin: 15px 0;"><strong>Get equity</strong> - Convert POT to ownership or earn directly</li>
                <li style="margin: 15px 0;"><strong>Build together</strong> - We all own paradise on Earth</li>
            </ol>
        </div>

        <h2 style="text-align: center; color: white; font-size: 2.5em; margin: 40px 0;">Available Opportunities</h2>

        <div class="task-grid">
            <div class="task-card">
                <div class="task-title">🚀 Share on Social</div>
                <p>One-click sharing on Reddit or LinkedIn</p>
                <p><strong>Time:</strong> 30 seconds</p>
                <div class="task-reward">100 POT</div>
            </div>

            <div class="task-card">
                <div class="task-title">✍️ Write a Review</div>
                <p>Share your I MATCH experience</p>
                <p><strong>Time:</strong> 5 minutes</p>
                <div class="task-reward">500 POT + 0.001% equity</div>
            </div>

            <div class="task-card">
                <div class="task-title">🤝 Recruit an Advisor</div>
                <p>Invite a financial advisor you trust</p>
                <p><strong>Time:</strong> 10 minutes</p>
                <div class="task-reward">1,000 POT + 0.01% equity + 10% revenue share</div>
            </div>

            <div class="task-card">
                <div class="task-title">💼 Community Manager</div>
                <p>Help users, answer questions, build community</p>
                <p><strong>Time:</strong> 10 hours/week</p>
                <div class="task-reward">$2,000/month + 0.5% equity</div>
            </div>

            <div class="task-card">
                <div class="task-title">📈 Growth Helper</div>
                <p>Marketing, outreach, provider recruitment</p>
                <p><strong>Time:</strong> 5 hours/week</p>
                <div class="task-reward">$1,000/month + 0.25% equity</div>
            </div>

            <div class="task-card">
                <div class="task-title">⚙️ Technical Helper</div>
                <p>Build features, fix bugs, improve automation</p>
                <p><strong>Time:</strong> Flexible</p>
                <div class="task-reward">$50/hour + 0.1% equity per 100 hours</div>
            </div>
        </div>

        <div style="text-align: center; margin-top: 60px;">
            <a href="/contribute/tasks?user_id=1" class="btn">View All Tasks →</a>
            <p style="color: white; margin-top: 20px; font-size: 1.2em;">Start earning today. Build paradise tomorrow.</p>
        </div>
    </div>
</body>
</html>
    """
    return HTMLResponse(content=html)
