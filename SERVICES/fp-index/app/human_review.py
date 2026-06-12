"""
Human Review Loop — Proactive approval workflow.

The system doesn't wait for humans to check a dashboard.
It emails pending items with one-click approve/reject links,
and actuates immediately on approval.

Flow:
  1. Adoption cycle flags item as needs_human_review
  2. System emails reviewer with context + approve/reject links
  3. Reviewer clicks link → API processes decision
  4. On approve → status = "adopted" → actuator fires → content published
  5. On reject → status = "dismissed" with reason
  6. Reminder sent if items sit unreviewed for 24h+
"""

import hashlib
import hmac
import logging
import os
import smtplib
import uuid
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, desc

from .models.database import ExecutionBriefRow, async_session
from .actuators import run_actuators
from .principles import classify_adoption

logger = logging.getLogger("fp_index.review")

router = APIRouter()

BASE_URL = "https://fullpotential.ai"
REVIEW_SECRET = os.getenv("REVIEW_SECRET", "fpai-review-2026")
REVIEWER_EMAIL = os.getenv("REVIEWER_EMAIL", "james@fullpotential.com")


def _sign_action(proposal_id: int, action: str) -> str:
    """HMAC signature so approve/reject links can't be guessed."""
    msg = f"{proposal_id}:{action}:{REVIEW_SECRET}"
    return hashlib.sha256(msg.encode()).hexdigest()[:16]


def _make_link(proposal_id: int, action: str) -> str:
    token = _sign_action(proposal_id, action)
    return f"{BASE_URL}/api/v1/review/{action}?id={proposal_id}&token={token}"


def _verify_token(proposal_id: int, action: str, token: str) -> bool:
    expected = _sign_action(proposal_id, action)
    return hmac.compare_digest(token, expected)


# ═══════════════════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/v1/review/approve")
async def approve_proposal(id: int = Query(...), token: str = Query(...)):
    """One-click approve from email link. Moves to adopted → actuator fires."""
    if not _verify_token(id, "approve", token):
        raise HTTPException(status_code=403, detail="Invalid token")

    async with async_session() as session:
        brief = (await session.execute(
            select(ExecutionBriefRow).where(ExecutionBriefRow.id == id)
        )).scalars().first()

        if not brief:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if brief.status not in ("needs_human_review", "adopted"):
            return HTMLResponse(_result_page(
                "Already Processed",
                f"This proposal is already in status: {brief.status}",
                brief.entry_title,
            ))

        brief.status = "adopted"
        await session.commit()

        category, _ = classify_adoption(brief.implementation_path or "", "general")
        proposal = {
            "id": brief.id,
            "title": brief.entry_title,
            "entry_title": brief.entry_title,
            "category": category,
            "implementation_path": brief.implementation_path or "",
            "narrative": brief.narrative or "",
            "score": brief.relevance_score or 0,
            "domain": "general",
        }

    results = await run_actuators([proposal])
    success = any(r.get("success") for r in results)
    action = results[0].get("action_taken", "unknown") if results else "no actuator"
    content_id = results[0].get("content_id") if results else None

    if success and content_id:
        return HTMLResponse(_result_page(
            "Approved & Implemented",
            f"The system has acted on your approval. Action: {action}",
            brief.entry_title,
            content_url=f"{BASE_URL}/insights/{content_id}",
        ))
    elif success:
        return HTMLResponse(_result_page(
            "Approved & Implemented",
            f"Action taken: {action}",
            brief.entry_title,
        ))
    else:
        error = results[0].get("error", "unknown") if results else "no actuator ran"
        return HTMLResponse(_result_page(
            "Approved (Actuator Issue)",
            f"Approved, but actuator reported: {error}. Status set to adopted — will retry.",
            brief.entry_title,
        ))


@router.get("/api/v1/review/reject")
async def reject_proposal(id: int = Query(...), token: str = Query(...)):
    """One-click reject from email link."""
    if not _verify_token(id, "reject", token):
        raise HTTPException(status_code=403, detail="Invalid token")

    async with async_session() as session:
        brief = (await session.execute(
            select(ExecutionBriefRow).where(ExecutionBriefRow.id == id)
        )).scalars().first()

        if not brief:
            raise HTTPException(status_code=404, detail="Proposal not found")

        brief.status = "dismissed"
        brief.narrative = (brief.narrative or "") + " [HUMAN REJECTED]"
        await session.commit()

    return HTMLResponse(_result_page(
        "Rejected",
        "Proposal dismissed. The system won't act on this item.",
        brief.entry_title,
    ))


@router.get("/api/v1/review/pending")
async def get_pending_reviews():
    """JSON list of all items awaiting human review."""
    async with async_session() as session:
        items = (await session.execute(
            select(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "needs_human_review")
            .order_by(desc(ExecutionBriefRow.relevance_score))
        )).scalars().all()

    return {
        "count": len(items),
        "items": [
            {
                "id": r.id,
                "title": r.entry_title,
                "score": r.relevance_score,
                "narrative": r.narrative,
                "category": classify_adoption(r.implementation_path or "", "general")[0],
                "created_at": str(r.created_at),
                "approve_url": _make_link(r.id, "approve"),
                "reject_url": _make_link(r.id, "reject"),
            }
            for r in items
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Review Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

REVIEW_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:ital,wght@0,400;0,600;1,400&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#06060b;--card:#0c0c14;--border:#1a1a2e;--text:#c8c8d8;--dim:#666680;
      --accent:#00d4ff;--gold:#ffb800;--red:#ff4466;--green:#22cc88;--purple:#7b2fff}
body{font-family:'Newsreader',Georgia,serif;background:var(--bg);color:var(--text);line-height:1.7}
.wrap{max-width:860px;margin:0 auto;padding:40px 20px}
.site-header{text-align:center;padding:24px 0 32px;border-bottom:1px solid var(--border);margin-bottom:32px}
.site-header a{color:var(--dim);font-family:'IBM Plex Mono',monospace;font-size:0.7rem;
               text-transform:uppercase;letter-spacing:3px;text-decoration:none}
h1{font-size:1.6rem;color:#e8e8f8;text-align:center;margin-bottom:8px}
.subtitle{text-align:center;color:var(--dim);font-size:0.9rem;margin-bottom:32px}
.count-bar{display:flex;justify-content:center;gap:16px;margin-bottom:32px;font-family:'IBM Plex Mono',monospace;font-size:0.8rem}
.count-bar span{padding:6px 14px;background:var(--card);border:1px solid var(--border);border-radius:6px}
.count-bar b{color:var(--gold)}
.review-card{padding:24px;background:var(--card);border:1px solid var(--border);border-radius:10px;margin-bottom:16px;
             transition:border-color 0.2s}
.review-card:hover{border-color:var(--accent)}
.review-title{font-size:1rem;font-weight:600;color:#e0e0f0;margin-bottom:8px;line-height:1.4}
.review-meta{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);margin-bottom:12px;display:flex;gap:12px;flex-wrap:wrap}
.review-narrative{font-size:0.88rem;color:var(--dim);margin-bottom:16px;line-height:1.6}
.review-actions{display:flex;gap:10px}
.btn{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;padding:10px 24px;border-radius:6px;
     text-decoration:none;font-weight:600;transition:opacity 0.2s;display:inline-block}
.btn:hover{opacity:0.85;text-decoration:none}
.btn-approve{background:linear-gradient(135deg,var(--green),#1a9960);color:#fff}
.btn-reject{background:none;border:1px solid var(--border);color:var(--dim)}
.btn-reject:hover{border-color:var(--red);color:var(--red)}
.score{font-family:'IBM Plex Mono',monospace;font-weight:600}
.score-high{color:var(--gold)}
.score-med{color:var(--accent)}
.tag{padding:2px 8px;border-radius:3px;border:1px solid var(--border);font-size:0.65rem;text-transform:uppercase;letter-spacing:1px;
     font-family:'IBM Plex Mono',monospace}
.empty{text-align:center;padding:60px 20px;color:var(--dim);font-size:1rem}
.footer{margin-top:40px;text-align:center;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:#333;padding-top:20px;border-top:1px solid var(--border)}
.footer a{color:var(--dim);text-decoration:none}
"""


@router.get("/review", response_class=HTMLResponse)
async def review_dashboard():
    """Human review dashboard — shows all pending items with approve/reject."""
    async with async_session() as session:
        items = (await session.execute(
            select(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "needs_human_review")
            .order_by(desc(ExecutionBriefRow.relevance_score))
        )).scalars().all()

        total_implemented = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "implemented")
        )).scalar()

    cards = ""
    for r in items:
        category, _ = classify_adoption(r.implementation_path or "", "general")
        score = r.relevance_score or 0
        score_class = "score-high" if score >= 0.7 else "score-med"
        approve_url = _make_link(r.id, "approve")
        reject_url = _make_link(r.id, "reject")
        narrative = (r.narrative or "No narrative available.")[:300]
        age = ""
        if r.created_at:
            hours = (datetime.now(timezone.utc) - r.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            age = f"{int(hours)}h ago" if hours < 48 else f"{int(hours/24)}d ago"

        cards += f"""
<div class="review-card">
  <div class="review-title">{r.entry_title or 'Untitled'}</div>
  <div class="review-meta">
    <span class="score {score_class}">{score:.0%} match</span>
    <span class="tag">{category}</span>
    <span>{age}</span>
  </div>
  <div class="review-narrative">{narrative}</div>
  <div class="review-actions">
    <a href="{approve_url}" class="btn btn-approve" onclick="return confirm('Approve this proposal?')">Approve & Actuate</a>
    <a href="{reject_url}" class="btn btn-reject" onclick="return confirm('Reject this proposal?')">Dismiss</a>
  </div>
</div>"""

    if not cards:
        cards = '<div class="empty">No items waiting for review. The system is running autonomously.</div>'

    page = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Human Review — Full Potential AI</title>
<style>{REVIEW_CSS}</style>
</head><body>
<div class="wrap">
<div class="site-header"><a href="/">FULL POTENTIAL AI</a></div>
<h1>Pending Review</h1>
<p class="subtitle">These proposals scored high but need your approval before the system acts on them.</p>
<div class="count-bar">
  <span><b>{len(items)}</b> awaiting review</span>
  <span><b>{total_implemented}</b> implemented</span>
</div>
{cards}
<div class="footer">
  <a href="/insights">Insights</a> &middot;
  <a href="/intelligence">Intelligence</a> &middot;
  <a href="/">Home</a>
</div>
</div></body></html>"""
    return HTMLResponse(content=page)


# ═══════════════════════════════════════════════════════════════════════════════
# Proactive Email
# ═══════════════════════════════════════════════════════════════════════════════

async def send_review_digest():
    """Email the reviewer all pending items with approve/reject links.

    Called by the adoption cycle whenever new items enter needs_human_review,
    and by a daily reminder if items have been sitting for 24h+.
    """
    async with async_session() as session:
        items = (await session.execute(
            select(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "needs_human_review")
            .order_by(desc(ExecutionBriefRow.relevance_score))
            .limit(15)
        )).scalars().all()

    if not items:
        return {"sent": False, "reason": "no pending items"}

    rows_html = ""
    rows_plain = ""
    for r in items:
        category, _ = classify_adoption(r.implementation_path or "", "general")
        score = r.relevance_score or 0
        approve = _make_link(r.id, "approve")
        reject = _make_link(r.id, "reject")
        title = (r.entry_title or "Untitled")[:80]
        narrative = (r.narrative or "")[:150]

        rows_html += f"""
<tr>
  <td style="padding:12px;border-bottom:1px solid #1a1a2e">
    <div style="color:#e0e0f0;font-size:0.9rem;font-weight:600;margin-bottom:4px">{title}</div>
    <div style="color:#666;font-size:0.75rem;margin-bottom:8px">{narrative}</div>
    <div style="font-family:monospace;font-size:0.7rem;color:#666;margin-bottom:8px">{score:.0%} match · {category}</div>
    <a href="{approve}" style="display:inline-block;padding:6px 16px;background:#22cc88;color:#fff;text-decoration:none;border-radius:4px;font-size:0.8rem;font-weight:600;margin-right:8px">Approve</a>
    <a href="{reject}" style="display:inline-block;padding:6px 16px;border:1px solid #333;color:#666;text-decoration:none;border-radius:4px;font-size:0.8rem">Dismiss</a>
  </td>
</tr>"""

        rows_plain += f"\n{title}\n  Score: {score:.0%} | Category: {category}\n  {narrative}\n  Approve: {approve}\n  Reject: {reject}\n"

    subject = f"{len(items)} proposals need your approval — Full Potential AI"

    plain = f"""Full Potential AI — Human Review Required

{len(items)} proposals are waiting for your decision.
The system evaluated these as high-relevance but flagged them for human approval before acting.

Review all at once: {BASE_URL}/review
{rows_plain}
---
This email was sent by the Full Potential AI system because proposals are waiting.
"""

    html = f"""<!DOCTYPE html><html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#06060b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:600px;margin:0 auto;padding:32px 20px">

<div style="text-align:center;margin-bottom:24px">
  <a href="{BASE_URL}" style="color:#00d4ff;font-size:0.75rem;font-weight:600;letter-spacing:0.15em;text-decoration:none">FULL POTENTIAL AI</a>
  <div style="color:#666;font-size:0.65rem;margin-top:4px">HUMAN REVIEW REQUIRED</div>
</div>

<div style="color:#e0e0e0;font-size:1rem;font-weight:600;margin-bottom:8px;text-align:center">
  {len(items)} proposals need your approval
</div>
<div style="color:#666;font-size:0.85rem;margin-bottom:24px;text-align:center">
  The system will act immediately when you approve.
</div>

<div style="text-align:center;margin-bottom:24px">
  <a href="{BASE_URL}/review" style="display:inline-block;padding:12px 32px;background:linear-gradient(135deg,#00d4ff,#7b2fff);color:#fff;text-decoration:none;border-radius:6px;font-size:0.9rem;font-weight:600">Review All →</a>
</div>

<table style="width:100%;border-collapse:collapse;background:#0c0c14;border:1px solid #1a1a2e;border-radius:8px">
{rows_html}
</table>

<div style="margin-top:28px;text-align:center;color:#333;font-size:0.7rem">
  <a href="{BASE_URL}/review" style="color:#666">View review dashboard</a>
</div>

</div></body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = "Full Potential AI <noreply@fullpotential.ai>"
        msg["To"] = REVIEWER_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("localhost", 25) as smtp:
            smtp.send_message(msg)

        logger.info(f"[REVIEW] Sent review digest: {len(items)} items to {REVIEWER_EMAIL}")
        return {"sent": True, "items": len(items), "to": REVIEWER_EMAIL}
    except Exception as e:
        logger.error(f"[REVIEW] Failed to send digest: {e}")
        return {"sent": False, "error": str(e)}


async def send_review_notification(new_items: list[dict]):
    """Send immediate notification when new items enter needs_human_review.

    Called directly from the adoption cycle. Only sends if there are
    new items that haven't been notified about yet.
    """
    if not new_items:
        return

    count = len(new_items)
    titles = [item.get("title", "Untitled")[:60] for item in new_items[:5]]
    preview = "\n".join(f"  • {t}" for t in titles)

    subject = f"Action needed: {count} new proposal{'s' if count > 1 else ''} for review"

    plain = f"""Full Potential AI — New Proposals Need Review

{count} new proposal{'s have' if count > 1 else ' has'} been flagged for your approval:

{preview}

Review and approve: {BASE_URL}/review

The system will act immediately when you approve.
"""

    html = f"""<!DOCTYPE html><html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#06060b;font-family:-apple-system,sans-serif">
<div style="max-width:600px;margin:0 auto;padding:32px 20px">
<div style="text-align:center;margin-bottom:20px">
  <a href="{BASE_URL}" style="color:#00d4ff;font-size:0.75rem;font-weight:600;letter-spacing:0.15em;text-decoration:none">FULL POTENTIAL AI</a>
</div>
<div style="color:#e0e0e0;font-size:1rem;font-weight:600;text-align:center;margin-bottom:16px">
  {count} new proposal{'s need' if count > 1 else ' needs'} your approval
</div>
<div style="color:#888;font-size:0.85rem;margin-bottom:24px;white-space:pre-line">{preview}</div>
<div style="text-align:center">
  <a href="{BASE_URL}/review" style="display:inline-block;padding:12px 32px;background:linear-gradient(135deg,#22cc88,#1a9960);color:#fff;text-decoration:none;border-radius:6px;font-size:0.9rem;font-weight:600">Review & Approve →</a>
</div>
<div style="margin-top:24px;text-align:center;color:#444;font-size:0.75rem">The system will actuate immediately on approval.</div>
</div></body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = "Full Potential AI <noreply@fullpotential.ai>"
        msg["To"] = REVIEWER_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("localhost", 25) as smtp:
            smtp.send_message(msg)

        logger.info(f"[REVIEW] Notified {REVIEWER_EMAIL}: {count} new items for review")
    except Exception as e:
        logger.error(f"[REVIEW] Notification failed: {e}")


def _result_page(title: str, message: str, proposal_title: str, content_url: str = None) -> str:
    """Simple result page shown after approve/reject click."""
    content_link = ""
    if content_url:
        content_link = f'<a href="{content_url}" style="display:inline-block;margin-top:16px;padding:10px 24px;background:#00d4ff;color:#000;text-decoration:none;border-radius:6px;font-size:0.85rem;font-weight:600">View Published Content →</a>'

    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Full Potential AI</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:wght@400;600&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Newsreader',Georgia,serif;background:#06060b;color:#c8c8d8;display:flex;align-items:center;justify-content:center;min-height:100vh}}
.card{{max-width:500px;padding:48px;text-align:center}}
h1{{font-size:1.4rem;color:#e8e8f8;margin-bottom:12px}}
.msg{{color:#666680;font-size:0.92rem;margin-bottom:8px;line-height:1.6}}
.proposal{{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#444;margin-top:16px;padding:12px;background:#0c0c14;border:1px solid #1a1a2e;border-radius:6px}}
a.back{{display:inline-block;margin-top:24px;color:#00d4ff;font-size:0.85rem;text-decoration:none}}
</style></head><body>
<div class="card">
<h1>{title}</h1>
<div class="msg">{message}</div>
{content_link}
<div class="proposal">{proposal_title[:120]}</div>
<a class="back" href="/review">← Back to review queue</a>
</div></body></html>"""
