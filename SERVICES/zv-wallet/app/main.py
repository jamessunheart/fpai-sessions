"""ZV Wallet FastAPI service v0.1.

Endpoints map to SPEC.md. Webhook in: /wa/webhook. Witness + admin gated by X-Admin-Token.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import init_db, conn, audit_log, now_iso, MEDIA_DIR
from .mechanics import (
    TIER_VALUES, REDEMPTIONS, WEEKLY_CORA_CAP, trust_curve_pct,
    compute_seal, proof_to_cora, format_dollars,
)
from .commands import parse, HELP_PARTICIPANT, HELP_WITNESS
from . import evo
from . import p2p
from . import group_observer

ADMIN_TOKEN = os.environ.get("ZV_WALLET_ADMIN_TOKEN", "zv-wallet-dev-token")
STATIC_DIR = Path(__file__).parent.parent / "static"
DASHBOARD_DIR = Path(__file__).parent.parent / "dashboard"

app = FastAPI(title="ZV Wallet", version="0.1.0")
init_db()
p2p.init_p2p_schema()


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")


# ---------- Health ----------

@app.get("/health")
async def health():
    try:
        state = await evo.connection_state()
    except Exception as e:
        state = {"error": str(e)[:200], "note": "Evolution API not yet paired or unreachable"}
    return {"ok": True, "service": "zv-wallet", "version": "0.1.0", "evolution": state}


# ---------- WA transport ----------

@app.post("/wa/webhook")
async def wa_webhook(request: Request):
    """Evolution API global webhook. Stores message + dispatches handler."""
    body = await request.json()
    event = body.get("event") or body.get("eventType") or ""
    data = body.get("data") or {}

    # Always log raw payload for Phoenix discipline
    with conn() as c:
        c.execute(
            "INSERT INTO audit (actor, action, target, detail, ts) VALUES (?, ?, ?, ?, ?)",
            ("evolution", "webhook", event, json.dumps(body)[:2000], now_iso()),
        )

    if event in ("messages.upsert", "messages.upsert.received", "MESSAGES_UPSERT"):
        await handle_inbound(data)
    elif event in ("messages.reaction", "MESSAGES_REACTION", "messages.reaction.received"):
        try:
            await group_observer.process_reaction(data)
        except Exception as e:
            with conn() as c:
                c.execute(
                    "INSERT INTO audit (actor, action, target, detail, ts) VALUES (?, ?, ?, ?, ?)",
                    ("evolution", "reaction_error", "", str(e)[:300], now_iso()),
                )
    elif event in ("connection.update", "CONNECTION_UPDATE"):
        with conn() as c:
            c.execute(
                "INSERT INTO audit (actor, action, target, detail, ts) VALUES (?, ?, ?, ?, ?)",
                ("evolution", "connection_update", data.get("state", ""), json.dumps(data)[:500], now_iso()),
            )
    elif event in ("qrcode.updated", "QRCODE_UPDATED"):
        with conn() as c:
            c.execute(
                "INSERT INTO audit (actor, action, target, detail, ts) VALUES (?, ?, ?, ?, ?)",
                ("evolution", "qr_updated", "", "", now_iso()),
            )
    return {"ok": True}


async def handle_inbound(data: dict):
    """Process inbound WA message: store + dispatch command.

    Routing:
      - `<jid>@g.us`           -> group_observer (parse work claims · witness gate)
      - `<jid>@s.whatsapp.net` -> existing DM wallet handler (unchanged)
    """
    msg = data if data.get("key") else (data.get("messages", [{}])[0] if isinstance(data.get("messages"), list) else data)
    key = msg.get("key") or {}
    message_id = key.get("id") or ""
    remote = key.get("remoteJid") or ""
    from_me = key.get("fromMe", False)
    if from_me:
        return  # ignore our own outgoing

    # Group messages take a completely separate path (Work Credit observer).
    # The DM wallet handler below is unchanged.
    if remote.endswith("@g.us"):
        try:
            await group_observer.process_message(data)
        except Exception as e:
            with conn() as c:
                c.execute(
                    "INSERT INTO audit (actor, action, target, detail, ts) VALUES (?, ?, ?, ?, ?)",
                    ("evolution", "group_observer_error", message_id, str(e)[:300], now_iso()),
                )
        return

    phone = evo.extract_phone(remote)

    body_msg = msg.get("message") or {}
    text = (
        body_msg.get("conversation")
        or (body_msg.get("extendedTextMessage") or {}).get("text")
        or (body_msg.get("imageMessage") or {}).get("caption")
        or (body_msg.get("videoMessage") or {}).get("caption")
        or ""
    )
    media_path = None
    msg_type = "text"
    if "imageMessage" in body_msg:
        msg_type = "image"
        media_path = await evo.download_media(message_id)
    elif "videoMessage" in body_msg:
        msg_type = "video"
        media_path = await evo.download_media(message_id)
    elif "audioMessage" in body_msg:
        msg_type = "audio"
        media_path = await evo.download_media(message_id)
    elif "documentMessage" in body_msg:
        msg_type = "document"
        media_path = await evo.download_media(message_id)

    with conn() as c:
        try:
            c.execute(
                """INSERT OR IGNORE INTO wa_messages
                (wa_message_id, from_phone, direction, message_type, body, media_path, raw_payload, ts)
                VALUES (?, ?, 'in', ?, ?, ?, ?, ?)""",
                (message_id, phone, msg_type, text, media_path, json.dumps(msg)[:4000], now_iso()),
            )
        except Exception:
            pass

    await dispatch_command(phone, text, msg_type, media_path)


async def dispatch_command(phone: str, text: str, msg_type: str, media_path: str | None):
    """Parse + execute command per role."""
    if not text and media_path:
        # Bare media with no caption — treat as raw proof needing routing
        return await handle_bare_media(phone, msg_type, media_path)

    cmd = parse(text)
    role = get_role(phone)

    if cmd.verb == "" and msg_type == "text":
        # Unknown message — fall back to help based on role
        if role == "witness":
            await evo.send_text(phone, HELP_WITNESS)
        else:
            await evo.send_text(phone, HELP_PARTICIPANT)
        return

    if cmd.is_witness_command:
        if role != "witness":
            await evo.send_text(phone, "_Witness commands require witness role. Ask a steward to pair you._")
            return
        return await handle_witness_command(phone, cmd, media_path)
    else:
        return await handle_participant_command(phone, cmd, msg_type, media_path)


def get_role(phone: str) -> str:
    with conn() as c:
        r = c.execute("SELECT role FROM users WHERE phone = ?", (phone,)).fetchone()
    return r["role"] if r else "unknown"


# ---------- Participant commands ----------

async def handle_participant_command(phone: str, cmd, msg_type: str, media_path: str | None):
    if cmd.verb == "help":
        await evo.send_text(phone, HELP_PARTICIPANT)
        return
    if cmd.verb == "balance":
        bal = balance_for(phone)
        await evo.send_text(phone, format_balance(bal))
        return
    if cmd.verb == "invoice":
        inv = active_invoice(phone)
        if not inv:
            await evo.send_text(phone, "_No active invoice this week. Your witness will issue Monday._")
            return
        await evo.send_text(phone, format_invoice(inv))
        return
    if cmd.verb == "proof":
        priority = None
        body_text = " ".join(cmd.args)
        if cmd.args and cmd.args[0].lower() in ("p1", "p2", "p3"):
            priority = cmd.args[0].lower()
            body_text = " ".join(cmd.args[1:])
        await submit_proof(phone, priority, body_text, media_path)
        return
    if cmd.verb == "redeem":
        if not cmd.args:
            await evo.send_text(phone, "Try: `redeem coconut` — see menu at zenvillage.app/wallet")
            return
        item = cmd.args[0].lower()
        await request_redemption(phone, item)
        return
    if cmd.verb == "transfer":
        await handle_transfer(phone, cmd)
        return
    if cmd.verb == "history":
        await handle_history(phone)
        return
    # Unknown
    await evo.send_text(phone, HELP_PARTICIPANT)


# ---------- P2P transfer (v4.1) ----------

async def handle_transfer(sender_phone: str, cmd):
    """`/transfer @user 500 [memo...]` — wallet-to-wallet CORA transfer."""
    if len(cmd.args) < 2:
        await evo.send_text(
            sender_phone,
            "Usage: `/transfer @recipient <amount> [memo]`\n"
            "Example: `/transfer @maria 50 thanks for the smoothie`",
        )
        return
    recipient_token = cmd.args[0]
    try:
        amount = int(cmd.args[1])
    except ValueError:
        await evo.send_text(sender_phone, "Amount must be a whole number of CORA.")
        return
    memo = " ".join(cmd.args[2:]) if len(cmd.args) > 2 else None

    try:
        rec = p2p.execute_transfer(sender_phone, recipient_token, amount, memo)
    except p2p.TransferError as e:
        await evo.send_text(sender_phone, f"✗ Transfer failed: {e}")
        return

    # Confirm both parties
    await evo.send_text(sender_phone, p2p.format_transfer_confirmation(rec, "sender"))
    await evo.send_text(rec["to_phone"], p2p.format_transfer_confirmation(rec, "receiver"))

    # Large-transfer steward visibility (not approval-gated)
    if rec["large_flag"]:
        await _notify_stewards_large_transfer(rec)


async def handle_history(phone: str):
    rows = p2p.personal_history(phone, limit=10)
    await evo.send_text(phone, p2p.format_history(rows, phone))


async def _notify_stewards_large_transfer(rec: dict):
    """Push a visibility-only notification to all steward phones."""
    with conn() as c:
        stewards = c.execute(
            "SELECT phone FROM users WHERE role = 'steward' AND active = 1"
        ).fetchall()
    msg = (
        f"⚑ *Large transfer flagged* (visibility only · not gated)\n"
        f"#{rec['id']} · {rec['from_phone']} → {rec['to_phone']} · "
        f"{rec['amount']} CORA"
        f"{' · memo: ' + rec['memo'] if rec.get('memo') else ''}"
    )
    delivered = 0
    for row in stewards:
        try:
            await evo.send_text(row["phone"], msg)
            delivered += 1
        except Exception:
            pass
    p2p.mark_steward_notified(rec["id"])
    audit_log("system", "large_xfer_notified", str(rec["id"]),
              f"delivered to {delivered} stewards")


async def handle_bare_media(phone: str, msg_type: str, media_path: str | None):
    # Treat as proof without priority
    await submit_proof(phone, None, f"[{msg_type} attachment]", media_path)


async def submit_proof(phone: str, priority: str | None, body: str, media_path: str | None):
    inv = active_invoice(phone)
    if not inv:
        await evo.send_text(phone, "_No active invoice — proof can't be filed. Talk to your witness._")
        return
    with conn() as c:
        cur = c.execute(
            """INSERT INTO proofs
            (invoice_id, participant_phone, priority, content_text, media_path, media_type, submitted_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (inv["id"], phone, priority, body, media_path,
             "image" if (media_path or "").endswith(((".jpg", ".png", ".webp"))) else
             "video" if (media_path or "").endswith((".mp4",)) else
             "audio" if (media_path or "").endswith((".ogg", ".mp3", ".wav")) else
             "document" if media_path else "text",
             now_iso())
        )
        proof_id = cur.lastrowid
    audit_log(phone, "proof_submitted", str(proof_id), priority or "no-priority")
    label = priority.upper() if priority else "general"
    confirmation = f"✓ Proof #{proof_id} received ({label})\n_Witness will review at next check-in._"
    await evo.send_text(phone, confirmation)

    # Notify witness
    witness = paired_witness(phone)
    if witness:
        queue_count = pending_proof_count(witness)
        notif = f"📥 New proof #{proof_id} from {phone} ({label})\nQueue size: {queue_count}\nReview: `/approve {proof_id}` or `/partial {proof_id} <note>` or `/reject {proof_id} <note>`"
        await evo.send_text(witness, notif)


async def request_redemption(phone: str, item: str):
    item = item.lower()
    if item not in REDEMPTIONS:
        menu = "\n".join(f"`redeem {k}` — {v['cost']} CORA" for k, v in REDEMPTIONS.items())
        await evo.send_text(phone, f"Unknown item. Menu:\n{menu}")
        return
    cost = REDEMPTIONS[item]["cost"]
    bal = balance_for(phone)
    if bal["balance"] < cost:
        await evo.send_text(phone, f"Insufficient CORA. Need {cost}, have {bal['balance']}.")
        return
    # TODO: enforce caps (daily/monthly/yearly) — v0.2
    with conn() as c:
        cur = c.execute(
            """INSERT INTO redemptions (participant_phone, item, cora_cost, requested_at)
            VALUES (?, ?, ?, ?)""",
            (phone, item, cost, now_iso())
        )
        rid = cur.lastrowid
        # Deduct + ledger
        c.execute("UPDATE cora_balances SET balance = balance - ?, lifetime_spent = lifetime_spent + ?, updated_at = ? WHERE phone = ?",
                  (cost, cost, now_iso(), phone))
        c.execute("INSERT INTO cora_ledger (phone, delta, reason, ref_id, balance_after, ts) VALUES (?, ?, ?, ?, ?, ?)",
                  (phone, -cost, f"redeem_{item}", rid, bal["balance"] - cost, now_iso()))
    audit_log(phone, "redemption_requested", item, f"{cost} CORA")
    await evo.send_text(phone, f"✓ Redemption requested: {item} ({cost} CORA)\nSteward will fulfill. Balance: {bal['balance'] - cost} CORA.")


# ---------- Witness commands ----------

async def handle_witness_command(phone: str, cmd, media_path: str | None):
    if cmd.verb == "help":
        await evo.send_text(phone, HELP_WITNESS)
        return
    if cmd.verb == "queue":
        items = pending_proofs_for(phone)
        if not items:
            await evo.send_text(phone, "✓ Queue empty.")
            return
        txt = f"*Queue ({len(items)} pending):*\n" + "\n".join(
            f"#{p['id']} · {p['participant_phone']} · {(p['priority'] or '-').upper()} · {(p['content_text'] or '')[:60]}"
            for p in items[:20]
        )
        await evo.send_text(phone, txt)
        return
    if cmd.verb in ("approve", "partial", "reject"):
        if not cmd.args:
            await evo.send_text(phone, f"Usage: `/{cmd.verb} <proof_id> [note]`")
            return
        try:
            proof_id = int(cmd.args[0])
        except ValueError:
            await evo.send_text(phone, "Proof ID must be a number.")
            return
        note = " ".join(cmd.args[1:]) or None
        status = {"approve": "approved", "partial": "partial", "reject": "rejected"}[cmd.verb]
        decide_proof(proof_id, phone, status, note)
        return
    if cmd.verb == "seal":
        if not cmd.args:
            await evo.send_text(phone, "Usage: `/seal <participant_phone>`")
            return
        target = cmd.args[0].lstrip("@")
        await seal_week(target, phone)
        return
    if cmd.verb == "issue":
        if not cmd.args or "tier" not in cmd.kwargs:
            await evo.send_text(phone, 'Usage: `/issue <phone> tier:shared p1:"..." p2:"..." p3:"..."`')
            return
        target = cmd.args[0].lstrip("@")
        tier = cmd.kwargs["tier"]
        p1 = cmd.kwargs.get("p1", "(not set)")
        p2 = cmd.kwargs.get("p2", "(not set)")
        p3 = cmd.kwargs.get("p3", "(not set)")
        await issue_invoice(target, tier, p1, p2, p3, phone)
        return
    if cmd.verb == "pair":
        if not cmd.args:
            await evo.send_text(phone, "Usage: `/pair <participant_phone>`")
            return
        target = cmd.args[0].lstrip("@")
        pair_witness(target, phone)
        await evo.send_text(phone, f"✓ Paired as witness for {target}.")
        return
    await evo.send_text(phone, HELP_WITNESS)


def decide_proof(proof_id: int, witness_phone: str, status: str, note: str | None):
    with conn() as c:
        p = c.execute("SELECT * FROM proofs WHERE id = ?", (proof_id,)).fetchone()
        if not p:
            return
        cora = proof_to_cora(p["priority"], status)
        c.execute(
            "UPDATE proofs SET status = ?, witness_phone = ?, witness_note = ?, witness_decision_at = ?, cora_awarded = ? WHERE id = ?",
            (status, witness_phone, note, now_iso(), cora, proof_id),
        )
        if cora > 0:
            credit_cora(p["participant_phone"], cora, f"proof_{status}_p{p['priority']}", proof_id)
    audit_log(witness_phone, f"proof_{status}", str(proof_id), note or "")
    # Notify participant
    import asyncio
    asyncio.create_task(evo.send_text(p["participant_phone"], f"Proof #{proof_id} {status.upper()}{f' (+{cora} CORA)' if cora else ''}{(' — ' + note) if note else ''}"))


def credit_cora(phone: str, amount: int, reason: str, ref_id: int | None = None):
    with conn() as c:
        c.execute(
            """INSERT INTO cora_balances (phone, balance, lifetime_earned, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
              balance = balance + excluded.balance,
              lifetime_earned = lifetime_earned + excluded.lifetime_earned,
              updated_at = excluded.updated_at""",
            (phone, amount, amount, now_iso())
        )
        bal = c.execute("SELECT balance FROM cora_balances WHERE phone = ?", (phone,)).fetchone()["balance"]
        c.execute(
            "INSERT INTO cora_ledger (phone, delta, reason, ref_id, balance_after, ts) VALUES (?, ?, ?, ?, ?, ?)",
            (phone, amount, reason, ref_id, bal, now_iso())
        )


async def issue_invoice(participant_phone: str, tier: str, p1: str, p2: str, p3: str, witness_phone: str):
    if tier not in TIER_VALUES:
        await evo.send_text(witness_phone, f"Invalid tier '{tier}'. Use private/shared/communal.")
        return
    with conn() as c:
        u = c.execute("SELECT * FROM users WHERE phone = ?", (participant_phone,)).fetchone()
        if not u:
            # Auto-onboard at this point
            c.execute(
                "INSERT INTO users (phone, role, tier, week_number, active, onboarded_at) VALUES (?, 'participant', ?, 1, 1, ?)",
                (participant_phone, tier, now_iso())
            )
            week_num = 1
        else:
            week_num = (u["week_number"] or 0) + 1
            c.execute("UPDATE users SET week_number = ?, tier = ? WHERE phone = ?", (week_num, tier, participant_phone))
        tv = TIER_VALUES[tier]
        # Monday of current week (UTC heuristic; for v0.1)
        today = datetime.now(timezone.utc).date()
        monday = today - timedelta(days=today.weekday())
        cur = c.execute(
            """INSERT INTO invoices
            (participant_phone, week_start, tier, value_stack_cents, floor_cents, trust_curve_pct, p1, p2, p3, issued_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (participant_phone, monday.isoformat(), tier, tv["value_stack"], tv["floor"],
             trust_curve_pct(week_num), p1, p2, p3, now_iso())
        )
        invoice_id = cur.lastrowid
        # Ensure pairing exists
        existing = c.execute(
            "SELECT id FROM witness_pairings WHERE participant_phone = ? AND witness_phone = ? AND active = 1",
            (participant_phone, witness_phone)
        ).fetchone()
        if not existing:
            c.execute(
                "INSERT INTO witness_pairings (participant_phone, witness_phone, paired_at, active) VALUES (?, ?, ?, 1)",
                (participant_phone, witness_phone, now_iso())
            )
    audit_log(witness_phone, "invoice_issued", str(invoice_id), f"week {week_num} · tier {tier}")
    msg = format_invoice({
        "id": invoice_id, "tier": tier, "week_number": week_num,
        "value_stack_cents": tv["value_stack"], "floor_cents": tv["floor"],
        "trust_curve_pct": trust_curve_pct(week_num),
        "p1": p1, "p2": p2, "p3": p3, "week_start": monday.isoformat(),
    })
    await evo.send_text(participant_phone, msg)
    await evo.send_text(witness_phone, f"✓ Invoice #{invoice_id} issued to {participant_phone} (week {week_num} · {tier}).")


async def seal_week(participant_phone: str, witness_phone: str):
    inv = active_invoice(participant_phone)
    if not inv:
        await evo.send_text(witness_phone, f"No active invoice for {participant_phone}.")
        return
    with conn() as c:
        u = c.execute("SELECT week_number FROM users WHERE phone = ?", (participant_phone,)).fetchone()
        week_num = (u["week_number"] if u else 1) or 1
        # Aggregate proofs for this invoice
        proofs = c.execute(
            "SELECT priority, status, COUNT(*) AS cnt FROM proofs WHERE invoice_id = ? GROUP BY priority, status",
            (inv["id"],)
        ).fetchall()
        proof_count = sum(p["cnt"] for p in proofs)
        p_status = {"p1": "none", "p2": "none", "p3": "none"}
        for p in proofs:
            if p["priority"] in p_status and p["status"] == "approved":
                p_status[p["priority"]] = "full"
            elif p["priority"] in p_status and p["status"] == "partial" and p_status[p["priority"]] == "none":
                p_status[p["priority"]] = "partial"
        # Hours: estimate 1 hour per approved priority proof (placeholder; v0.2 logs hours explicitly)
        hours = c.execute(
            "SELECT COUNT(*) AS c FROM proofs WHERE invoice_id = ? AND status IN ('approved', 'partial')",
            (inv["id"],)
        ).fetchone()["c"] * 2  # rough estimate: 2 hrs per proof
        hours = min(hours, 20)  # cap at the weekly 20-hr baseline

        seal = compute_seal(
            tier=inv["tier"], week_number=week_num, hours_logged=hours,
            p1_status=p_status["p1"], p2_status=p_status["p2"], p3_status=p_status["p3"],
        )

        narrative = format_seal_narrative(inv, seal, hours, p_status, proof_count)

        c.execute(
            """INSERT INTO weekly_seals
            (invoice_id, participant_phone, hours_logged, p1_status, p2_status, p3_status, proof_count,
             hourly_offset_cents, invoice_reduction_cents, final_due_cents, cora_earned_raw, cora_capped, honor_entries,
             sealed_at, witness_phone, narrative)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (inv["id"], participant_phone, hours, p_status["p1"], p_status["p2"], p_status["p3"], proof_count,
             seal["hourly_credit_cents"], seal["invoice_reduction_cents"], seal["final_due_cents"],
             seal["cora_raw"], seal["cora_earned"], seal["honor_entries"], now_iso(), witness_phone, narrative)
        )
        c.execute(
            "UPDATE invoices SET sealed = 1, final_due_cents = ?, final_cora_earned = ?, final_honor_entry = ? WHERE id = ?",
            (seal["final_due_cents"], seal["cora_earned"], seal["honor_entries"], inv["id"])
        )
    # Credit CORA earned this week (proof-by-proof already credited but we top-up if seal has extras)
    extra = seal["cora_earned"] - balance_earned_this_week(participant_phone, inv["id"])
    if extra > 0:
        credit_cora(participant_phone, extra, f"weekly_seal_w{week_num}", inv["id"])
    audit_log(witness_phone, "weekly_seal", participant_phone, f"week {week_num} · due {seal['final_due_cents']}c · cora {seal['cora_earned']}")
    await evo.send_text(participant_phone, narrative)
    await evo.send_text(witness_phone, f"✓ Sealed week {week_num} for {participant_phone}.\n{narrative}")


def balance_earned_this_week(phone: str, invoice_id: int) -> int:
    with conn() as c:
        r = c.execute(
            "SELECT COALESCE(SUM(delta), 0) AS s FROM cora_ledger WHERE phone = ? AND delta > 0 AND ref_id = ?",
            (phone, invoice_id)
        ).fetchone()
    return r["s"] or 0


# ---------- Helpers ----------

def balance_for(phone: str) -> dict:
    with conn() as c:
        r = c.execute("SELECT * FROM cora_balances WHERE phone = ?", (phone,)).fetchone()
        ledger = c.execute(
            "SELECT delta, reason, ts FROM cora_ledger WHERE phone = ? ORDER BY id DESC LIMIT 10",
            (phone,)
        ).fetchall()
    bal = dict(r) if r else {"phone": phone, "balance": 0, "lifetime_earned": 0, "lifetime_spent": 0, "honor_entries": 0}
    bal["recent"] = [dict(row) for row in ledger]
    return bal


def active_invoice(phone: str) -> dict | None:
    with conn() as c:
        r = c.execute(
            "SELECT * FROM invoices WHERE participant_phone = ? AND sealed = 0 ORDER BY id DESC LIMIT 1",
            (phone,)
        ).fetchone()
    return dict(r) if r else None


def paired_witness(participant_phone: str) -> str | None:
    with conn() as c:
        r = c.execute(
            "SELECT witness_phone FROM witness_pairings WHERE participant_phone = ? AND active = 1 ORDER BY id DESC LIMIT 1",
            (participant_phone,)
        ).fetchone()
    return r["witness_phone"] if r else None


def pending_proofs_for(witness_phone: str) -> list[dict]:
    with conn() as c:
        # Get all participants paired with this witness, then their pending proofs
        r = c.execute(
            """SELECT p.* FROM proofs p
            JOIN witness_pairings wp ON wp.participant_phone = p.participant_phone AND wp.active = 1
            WHERE wp.witness_phone = ? AND p.status = 'pending'
            ORDER BY p.id ASC""",
            (witness_phone,)
        ).fetchall()
    return [dict(row) for row in r]


def pending_proof_count(witness_phone: str) -> int:
    return len(pending_proofs_for(witness_phone))


def pair_witness(participant_phone: str, witness_phone: str):
    with conn() as c:
        c.execute("UPDATE witness_pairings SET active = 0 WHERE participant_phone = ?", (participant_phone,))
        c.execute(
            "INSERT INTO witness_pairings (participant_phone, witness_phone, paired_at, active) VALUES (?, ?, ?, 1)",
            (participant_phone, witness_phone, now_iso())
        )
        # Auto-mark witness role
        c.execute(
            """INSERT INTO users (phone, role, active, onboarded_at) VALUES (?, 'witness', 1, ?)
            ON CONFLICT(phone) DO UPDATE SET role = 'witness'""",
            (witness_phone, now_iso())
        )


# ---------- Format helpers ----------

def format_balance(bal: dict) -> str:
    lines = [f"*Your CORA balance: {bal['balance']}*"]
    if bal.get("honor_entries", 0):
        lines.append(f"_Honor entries this season: {bal['honor_entries']}_")
    if bal.get("recent"):
        lines.append("\n_Recent activity:_")
        for r in bal["recent"][:5]:
            sign = "+" if r["delta"] > 0 else ""
            lines.append(f"  {sign}{r['delta']} · {r['reason']}")
    return "\n".join(lines)


def format_invoice(inv: dict) -> str:
    tier = inv["tier"]
    week = inv.get("week_number") or "?"
    return (
        f"*🏯 Zen Village · Week {week} · Invoice #{inv.get('id', '?')}*\n"
        f"_Tier: {tier} · Week starting {inv['week_start']}_\n\n"
        f"Value stack: {format_dollars(inv['value_stack_cents'])}\n"
        f"Floor (always due): {format_dollars(inv['floor_cents'])}\n"
        f"Trust curve: {inv['trust_curve_pct']}% reduction available\n\n"
        f"*Your 3 priorities:*\n"
        f"P1: {inv['p1']}\n"
        f"P2: {inv['p2']}\n"
        f"P3: {inv['p3']}\n\n"
        f"_Hit them by Sunday Seal. Submit proof as you go:_\n"
        f"`proof p1 <text/photo/video>` etc.\n"
        f"_20 hrs + 3 priorities + strong proof = floor only + up to 250 CORA._"
    )


def format_seal_narrative(inv: dict, seal: dict, hours: int, p_status: dict, proof_count: int) -> str:
    return (
        f"*🌀 Sunday Seal · Week locked*\n"
        f"_Tier: {inv['tier']} · Hours: {hours} · Proofs reviewed: {proof_count}_\n\n"
        f"P1: {p_status['p1'].upper()}\n"
        f"P2: {p_status['p2'].upper()}\n"
        f"P3: {p_status['p3'].upper()}\n\n"
        f"Value: {format_dollars(seal['value_stack_cents'])}\n"
        f"Reduction: −{format_dollars(seal['invoice_reduction_cents'])}\n"
        f"*You owe: {format_dollars(seal['final_due_cents'])}*\n\n"
        f"CORA earned: *{seal['cora_earned']}*"
        + (f" (+{seal['honor_entries']} honor entries)" if seal["honor_entries"] else "")
        + "\n_Next Monday: fresh cycle._"
    )


# ---------- REST: read endpoints ----------

@app.get("/wallet/balance/{phone}")
async def wallet_balance(phone: str):
    return balance_for(phone)


@app.get("/wallet/invoice/{phone}")
async def wallet_invoice(phone: str):
    inv = active_invoice(phone)
    if not inv:
        raise HTTPException(404, "no active invoice")
    return inv


@app.get("/wallet/redemptions")
async def wallet_redemptions():
    return REDEMPTIONS


@app.get("/wallet/seal/{phone}")
async def wallet_seal_latest(phone: str):
    with conn() as c:
        r = c.execute(
            "SELECT * FROM weekly_seals WHERE participant_phone = ? ORDER BY id DESC LIMIT 1",
            (phone,)
        ).fetchone()
    if not r:
        raise HTTPException(404, "no seal yet")
    return dict(r)


# ---------- REST: P2P transfer (v4.1) ----------

class TransferReq(BaseModel):
    from_phone: str
    to_phone: str
    amount: int
    memo: str | None = None


@app.post("/wallet/transfer")
async def wallet_transfer(req: TransferReq):
    """Wallet-to-wallet CORA transfer. v4.1 P2P feature.

    No auth — caller phone identity is trusted from WA webhook context in v0.1.
    For dashboard-initiated transfers, require admin token at the gateway.
    """
    try:
        rec = p2p.execute_transfer(req.from_phone, req.to_phone, req.amount, req.memo)
    except p2p.TransferError as e:
        raise HTTPException(400, str(e))
    # Surface notifications via WA (best-effort)
    try:
        await evo.send_text(rec["from_phone"], p2p.format_transfer_confirmation(rec, "sender"))
        await evo.send_text(rec["to_phone"], p2p.format_transfer_confirmation(rec, "receiver"))
    except Exception:
        pass
    if rec["large_flag"]:
        try:
            await _notify_stewards_large_transfer(rec)
        except Exception:
            pass
    return rec


@app.get("/wallet/history/{phone}")
async def wallet_history(phone: str, limit: int = 10):
    """Personal P2P transaction history for this phone."""
    return {"phone": phone, "transfers": p2p.personal_history(phone, limit=limit)}


@app.get("/wallet/transfers/all", dependencies=[Depends(require_admin)])
async def wallet_transfers_all(
    limit: int = 200,
    counterparty: str | None = None,
    since: str | None = None,
    until: str | None = None,
):
    """Steward read-only view across all transfers, with filters."""
    return {
        "transfers": p2p.all_transfers(
            limit=limit, counterparty=counterparty, since=since, until=until
        )
    }


@app.get("/wallet/governance")
async def wallet_governance():
    """Discoverable governance rules — peer-to-peer-only, no exchange, etc."""
    return {
        "governance_locked": p2p.GOVERNANCE_LOCKED,
        "large_transfer_threshold": p2p.LARGE_TRANSFER_THRESHOLD,
        "disclaimer": p2p.DISCLAIMER,
        "change_requires": "CORA Nation governance approval (not Ember/Forge unilateral)",
    }


# ---- Explicit exchange rejection (v4.1 contract) ----
# Any third-party exchange integration attempt is rejected by design.
# These routes exist to make the policy machine-readable and easy to point to.

@app.post("/exchange/connect")
@app.post("/exchange/withdraw")
@app.post("/exchange/deposit")
@app.post("/wallet/cash/buy")
@app.post("/wallet/cash/sell")
async def exchange_rejected():
    raise HTTPException(status_code=403, detail=p2p.REJECT_EXCHANGE_REASON)


# ---------- REST: witness endpoints ----------

class IssueInvoiceReq(BaseModel):
    participant_phone: str
    witness_phone: str
    tier: str
    p1: str
    p2: str
    p3: str


@app.post("/witness/invoice/issue", dependencies=[Depends(require_admin)])
async def witness_issue(req: IssueInvoiceReq):
    await issue_invoice(req.participant_phone, req.tier, req.p1, req.p2, req.p3, req.witness_phone)
    return {"ok": True}


class ProofDecisionReq(BaseModel):
    witness_phone: str
    note: str | None = None


@app.post("/witness/proof/{proof_id}/approve", dependencies=[Depends(require_admin)])
async def witness_approve(proof_id: int, req: ProofDecisionReq):
    decide_proof(proof_id, req.witness_phone, "approved", req.note)
    return {"ok": True}


@app.post("/witness/proof/{proof_id}/partial", dependencies=[Depends(require_admin)])
async def witness_partial(proof_id: int, req: ProofDecisionReq):
    decide_proof(proof_id, req.witness_phone, "partial", req.note)
    return {"ok": True}


@app.post("/witness/proof/{proof_id}/reject", dependencies=[Depends(require_admin)])
async def witness_reject(proof_id: int, req: ProofDecisionReq):
    decide_proof(proof_id, req.witness_phone, "rejected", req.note)
    return {"ok": True}


@app.get("/witness/queue/{witness_phone}", dependencies=[Depends(require_admin)])
async def witness_queue(witness_phone: str):
    return {"pending": pending_proofs_for(witness_phone)}


@app.post("/witness/seal/{participant_phone}", dependencies=[Depends(require_admin)])
async def witness_seal(participant_phone: str, witness_phone: str = ""):
    await seal_week(participant_phone, witness_phone)
    return {"ok": True}


@app.post("/witness/pair", dependencies=[Depends(require_admin)])
async def witness_pair(participant_phone: str, witness_phone: str):
    pair_witness(participant_phone, witness_phone)
    return {"ok": True}


# ---------- Admin endpoints ----------

class OnboardReq(BaseModel):
    phone: str
    role: str = "participant"  # or 'witness'
    tier: str | None = None
    display_name: str | None = None
    witness_phone: str | None = None


@app.post("/admin/user/onboard", dependencies=[Depends(require_admin)])
async def admin_onboard(req: OnboardReq):
    with conn() as c:
        c.execute(
            """INSERT INTO users (phone, display_name, role, tier, week_number, active, onboarded_at)
            VALUES (?, ?, ?, ?, 0, 1, ?)
            ON CONFLICT(phone) DO UPDATE SET role = excluded.role, tier = excluded.tier, display_name = excluded.display_name""",
            (req.phone, req.display_name, req.role, req.tier, now_iso())
        )
    if req.role == "participant" and req.witness_phone:
        pair_witness(req.phone, req.witness_phone)
    audit_log("admin", "user_onboarded", req.phone, req.role)
    # Send welcome
    if req.role == "participant":
        welcome = (
            "🌀 Welcome to Zen Village.\n"
            "Reply `help` to see commands.\n"
            "Your witness will send your first invoice Monday.\n\n"
            + p2p.DISCLAIMER
        )
        await evo.send_text(req.phone, welcome)
    elif req.role == "witness":
        await evo.send_text(req.phone, "🌀 Witness role active.\nReply `/help` to see witness commands.")
    return {"ok": True}


@app.get("/admin/users", dependencies=[Depends(require_admin)])
async def admin_users():
    with conn() as c:
        users = c.execute("SELECT * FROM users ORDER BY onboarded_at DESC").fetchall()
    return {"users": [dict(u) for u in users]}


@app.get("/admin/audit", dependencies=[Depends(require_admin)])
async def admin_audit(limit: int = 100):
    with conn() as c:
        rows = c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return {"audit": [dict(r) for r in rows]}


@app.post("/admin/rotate", dependencies=[Depends(require_admin)])
async def admin_rotate():
    """Mark current WhatsApp pairing as rotated; ops team will re-pair via new QR."""
    audit_log("admin", "wa_rotation_started", evo.EVO_INSTANCE, "")
    return {"ok": True, "next_step": "POST /wa/qr to get fresh QR after recreating instance"}


# ---------- WA instance management ----------

@app.post("/wa/create", dependencies=[Depends(require_admin)])
async def wa_create():
    res = await evo.create_instance()
    return res


@app.get("/wa/qr", dependencies=[Depends(require_admin)])
async def wa_qr():
    return await evo.get_qr()


@app.get("/wa/status", dependencies=[Depends(require_admin)])
async def wa_status():
    return await evo.connection_state()


class SendReq(BaseModel):
    to_phone: str
    body: str


@app.post("/wa/send", dependencies=[Depends(require_admin)])
async def wa_send(req: SendReq):
    res = await evo.send_text(req.to_phone, req.body)
    return res


# ---------- PWA dashboard ----------

if DASHBOARD_DIR.exists():
    app.mount("/wallet/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="dashboard-static")


@app.get("/wallet/", response_class=HTMLResponse)
async def wallet_root():
    f = DASHBOARD_DIR / "index.html"
    if f.exists():
        return FileResponse(str(f))
    return HTMLResponse("<h1>ZV Wallet</h1><p>Dashboard not yet deployed.</p>")


# ---------- Public leaderboard (Group Observer v0.1) ----------

@app.get("/api/leaderboard")
async def api_leaderboard(week: str = "current"):
    """PUBLIC tier · aggregated WC stats only · no raw messages."""
    window = 7 * 24 * 3600
    # Future: `week=YYYY-WW` selector; v0.1 is rolling-7-day "current".
    snap = group_observer.leaderboard_snapshot(week_seconds=window)
    return snap


@app.get("/leaderboard/", response_class=HTMLResponse)
@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_root():
    f = DASHBOARD_DIR / "leaderboard.html"
    if f.exists():
        return FileResponse(str(f))
    return HTMLResponse(
        "<h1>ZV Work Credit Leaderboard</h1><p>Leaderboard not yet deployed.</p>"
    )


@app.get("/")
async def root():
    return {
        "service": "zv-wallet",
        "version": "0.1.0",
        "links": {
            "dashboard": "/wallet/",
            "leaderboard": "/leaderboard/",
            "leaderboard_api": "/api/leaderboard",
            "health": "/health",
        }
    }
