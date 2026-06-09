"""WhatsApp command parser + handlers.

Commands are case-insensitive. First word = verb.

Participant verbs:
    balance, invoice, help, redeem <item>
    proof p1 <text>, proof p2 <text>, proof p3 <text>, proof <text>

Witness verbs (slash-prefixed for distinction):
    /issue <participant_phone> tier:shared p1:"..." p2:"..." p3:"..."
    /approve <proof_id>
    /partial <proof_id> [reason]
    /reject <proof_id> [reason]
    /seal <participant_phone>
    /queue
    /pair <participant_phone>

Admin/onboarding (via PWA or admin endpoint):
    /onboard <phone> tier:shared witness:<witness_phone>
"""
from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class ParsedCommand:
    verb: str
    args: list[str]
    kwargs: dict[str, str]
    raw: str
    is_witness_command: bool


KV_PATTERN = re.compile(r'(\w+):(?:"([^"]+)"|(\S+))')


def parse(raw: str) -> ParsedCommand:
    text = (raw or "").strip()
    is_witness = text.startswith("/")
    if is_witness:
        text = text[1:].strip()
    parts = text.split(None, 1)
    if not parts:
        return ParsedCommand("", [], {}, raw, is_witness)
    verb = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    kwargs: dict[str, str] = {}
    for m in KV_PATTERN.finditer(rest):
        key = m.group(1).lower()
        val = m.group(2) or m.group(3)
        kwargs[key] = val
    # Strip kv pairs from rest for positional args
    positional_rest = KV_PATTERN.sub("", rest).strip()
    args = [a for a in positional_rest.split() if a]
    return ParsedCommand(verb, args, kwargs, raw, is_witness)


HELP_PARTICIPANT = """*Zen Village Wallet — quick commands*

`balance` — your CORA balance
`invoice` — this week's invoice + 3 priorities
`proof p1 <description>` — submit P1 proof (photo/video/voice OK as attachment)
`proof p2 <description>` — submit P2 proof
`proof p3 <description>` — submit P3 proof
`redeem coconut` — request a coconut (5 CORA)
`redeem smoothie` — request a smoothie (10 CORA)
`transfer @user <amount> [memo]` — send CORA to another member
`history` — your last 10 transactions
`help` — show this message

Witness pairs with you on Monday. Sunday Seal locks the week.

_CORA is peer-to-peer only between members. No cash exchange inside ZV channels.
No third-party exchanges connected. Governance changes require CORA Nation vote._"""


HELP_WITNESS = """*Zen Village Wallet — witness commands (DM only)*

`/queue` — proofs awaiting your review
`/approve <id>` — full credit
`/partial <id> [reason]` — partial credit
`/reject <id> [reason]` — reject
`/seal <participant_phone>` — generate Sunday Seal
`/issue <participant_phone> tier:shared p1:"..." p2:"..." p3:"..."` — issue Monday invoice
`/pair <participant_phone>` — pair as witness

Use PWA dashboard at zenvillage.app/wallet for richer view."""
