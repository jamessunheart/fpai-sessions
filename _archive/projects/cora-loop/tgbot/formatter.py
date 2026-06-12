"""Format cycle output for Telegram."""

from datetime import datetime, timezone


def format_cycle_summary(cycle_number, cora_directive, operator_report, steering_absorbed=0):
    """Format the cycle into a Telegram-friendly summary."""
    now = datetime.now(timezone.utc)
    ts = now.strftime("%B %d, %I:%M%p UTC")

    # Extract key sections from CORA (best effort — Phase 1 is prose)
    cora_short = cora_directive[:800] if cora_directive else "No directive generated."
    operator_short = operator_report[:800] if operator_report else "No report generated."

    parts = [
        f"🔄 *CYCLE {cycle_number}* — {ts}",
        "",
        "🎯 *CORA SAYS:*",
        cora_short,
        "",
        "📋 *OPERATOR STATUS:*",
        operator_short,
    ]

    if steering_absorbed > 0:
        parts.append("")
        parts.append(f"📨 _{steering_absorbed} steering message(s) absorbed this cycle_")

    parts.extend([
        "",
        "_Reply to steer. Or don't — we keep moving._",
    ])

    return "\n".join(parts)


def format_error(cycle_number, step, error):
    """Format an error alert for Telegram."""
    return (
        f"⚠️ *Cycle {cycle_number} failed at step: {step}*\n\n"
        f"Error: {str(error)[:500]}\n\n"
        f"System will retry once in 5 minutes."
    )


def format_health_lost():
    """Alert when no successful cycle in 8 hours."""
    return (
        "🚨 *System heartbeat lost*\n\n"
        "No successful CORA-Operator cycle in the last 8 hours.\n"
        "Manual check needed."
    )
