"""
classification_lib.py — shared redaction + check rules for the 4-tier classification system.

Used by classify_promote.py. Pure-Python, no external deps (stdlib only).

The 4 tiers (canonical):
    PRIVATE             → tier 0 (James + Ember only)
    COUNCIL-RESTRICTED  → tier 1 (inner AI council + sovereign humans)
    COUNCIL-OPEN        → tier 2 (Apprentice-tier+)
    PUBLIC              → tier 3 (everyone, including attackers)

Design contract:
    - All transformations are PROPOSALS (script writes to staging, never overwrites source)
    - Every redaction is logged with pattern + match + example
    - Higher-tier rules INHERIT lower-tier rules (T2 also applies T1)
    - Default classification when missing = PRIVATE (most restrictive)
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def utc_now():
    """timezone-aware UTC now (replacement for deprecated utcnow)."""
    return datetime.now(timezone.utc)

TIERS = {
    "PRIVATE": 0,
    "COUNCIL-RESTRICTED": 1,
    "COUNCIL-OPEN": 2,
    "PUBLIC": 3,
}
TIERS_REV = {v: k for k, v in TIERS.items()}

# Person allowlist (v0.1 hardcoded). Maintained list of names that appear in
# James's substrate and need role-tier abstraction at higher tiers.
# At T1+: replace with role
# At T3:  replace with generic "loved ones" / role gone entirely
PERSON_ABSTRACTIONS = {
    # Match (case-insensitive) → (T1+ replacement, T3 replacement)
    "cheyenne": ("primary partner", "loved ones"),
    "zenith":   ("family member",   "loved ones"),
    "zen":      ("family member",   "loved ones"),
    "halley":   ("an associate",    "an associate"),
    # James himself is allowed in higher tiers (he authors the work);
    # tracked here for completeness but no abstraction applied:
}


def classify_amount(amount_dollars: float) -> str:
    """Return a band-string for a dollar amount."""
    if amount_dollars < 500:
        return "modest ($X-range)"
    elif amount_dollars < 5_000:
        return "significant ($X-range)"
    else:
        return "substantial ($X-range)"


# ---------------------------------------------------------------------------
# Redaction patterns (each returns (replaced_text, list_of_redaction_records))
# ---------------------------------------------------------------------------

def _record(pattern_name: str, example: str) -> dict:
    return {"pattern": pattern_name, "example": example}


def redact_dollar_amounts(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Replace exact dollar amounts with abstracted bands at T1+."""
    if target_tier < 1:
        return text, []
    records: list[dict] = []

    # $1,234.56  or  $1.5k  or  $1234  (no trailing whitespace consumed)
    dollar_re = re.compile(r"\$([0-9]+(?:[,.][0-9]+)*)([kKmM]?)\b")

    def replace(m: re.Match) -> str:
        raw = m.group(0)
        num_str = m.group(1).replace(",", "")
        try:
            num = float(num_str)
        except ValueError:
            return raw
        suffix = m.group(2).lower()
        if suffix == "k":
            num *= 1_000
        elif suffix == "m":
            num *= 1_000_000
        band = classify_amount(num)
        records.append(_record("dollar_exact", f"{raw} → {band}"))
        return band

    new_text = dollar_re.sub(replace, text)
    return new_text, records


def redact_persons(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Replace person-specific references with role-tier abstraction.

    T1+: role-tier ("primary partner" etc.)
    T3:  even more abstracted ("loved ones")
    """
    if target_tier < 1:
        return text, []
    records: list[dict] = []
    new_text = text
    for name, (t1_replace, t3_replace) in PERSON_ABSTRACTIONS.items():
        # case-insensitive word-boundary match
        regex = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
        replacement = t3_replace if target_tier >= 3 else t1_replace
        if regex.search(new_text):
            count = len(regex.findall(new_text))
            records.append(_record("person_name", f"{name} (×{count}) → {replacement}"))
            new_text = regex.sub(replacement, new_text)
    return new_text, records


def redact_wallets(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Replace wallet addresses entirely at T1+."""
    if target_tier < 1:
        return text, []
    records: list[dict] = []
    new_text = text

    # EVM 0x + 40 hex
    evm_re = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
    matches = evm_re.findall(new_text)
    if matches:
        records.append(_record("wallet_evm", f"{matches[0][:10]}... (×{len(matches)})"))
        new_text = evm_re.sub("[WALLET-REDACTED]", new_text)

    # Solana base58 32-44 chars — heuristic (no 0/O/I/l)
    sol_re = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")
    # Be conservative: only match in contexts that suggest wallet (avoid hash/UUID false positives)
    # v0.1: only catch if preceded by wallet-like words on the same line
    wallet_context_re = re.compile(
        r"(?:wallet|address|account|sol|solana|deposit|withdraw)[^\n]{0,40}?"
        r"\b([1-9A-HJ-NP-Za-km-z]{32,44})\b",
        re.IGNORECASE,
    )
    sol_matches = wallet_context_re.findall(new_text)
    if sol_matches:
        records.append(_record("wallet_solana_heuristic", f"{sol_matches[0][:10]}... (×{len(sol_matches)})"))
        new_text = wallet_context_re.sub(lambda m: m.group(0).replace(m.group(1), "[WALLET-REDACTED]"), new_text)

    return new_text, records


def redact_api_keys(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Replace API keys / tokens at T1+."""
    if target_tier < 1:
        return text, []
    records: list[dict] = []
    new_text = text

    # Common token patterns: sk-..., pk-..., long hex/base64-ish secret strings, .token files
    patterns = [
        (r"\bsk-[A-Za-z0-9_-]{20,}\b", "openai_sk"),
        (r"\bsk_live_[A-Za-z0-9_-]{20,}\b", "stripe_live"),
        (r"\bsk_test_[A-Za-z0-9_-]{20,}\b", "stripe_test"),
        (r"\bxoxb-[A-Za-z0-9-]{10,}\b", "slack_bot"),
        (r"\bghp_[A-Za-z0-9]{20,}\b", "github_token"),
        (r"\bhf_[A-Za-z0-9]{20,}\b", "huggingface"),
        (r"\b[A-Fa-f0-9]{64}\b", "hex_secret_64"),  # heuristic for long hex secrets
    ]
    for regex_str, name in patterns:
        rx = re.compile(regex_str)
        matches = rx.findall(new_text)
        if matches:
            records.append(_record(f"api_key_{name}", f"{matches[0][:8]}... (×{len(matches)})"))
            new_text = rx.sub("[KEY-REDACTED]", new_text)

    return new_text, records


def redact_ips(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Replace IP addresses at T1+."""
    if target_tier < 1:
        return text, []
    records: list[dict] = []
    ip_re = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    matches = ip_re.findall(text)
    if not matches:
        return text, []
    # Filter common non-sensitive (0.0.0.0, 127.0.0.1, 255.255.255.255)
    sensitive = [ip for ip in matches if ip not in ("0.0.0.0", "127.0.0.1", "255.255.255.255")]
    if sensitive:
        records.append(_record("ip_address", f"{sensitive[0]} (×{len(sensitive)})"))
    new_text = ip_re.sub(
        lambda m: "[IP-REDACTED]" if m.group(0) not in ("0.0.0.0", "127.0.0.1", "255.255.255.255") else m.group(0),
        text,
    )
    return new_text, records


def redact_emails(text: str, target_tier: int) -> tuple[str, list[dict]]:
    if target_tier < 1:
        return text, []
    records: list[dict] = []
    email_re = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    matches = email_re.findall(text)
    if matches:
        records.append(_record("email", f"{matches[0]} (×{len(matches)})"))
    new_text = email_re.sub("[EMAIL-REDACTED]", text)
    return new_text, records


def redact_phones(text: str, target_tier: int) -> tuple[str, list[dict]]:
    if target_tier < 1:
        return text, []
    records: list[dict] = []
    # Conservative phone regex (avoid catching version numbers)
    phone_re = re.compile(r"\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b")
    matches = phone_re.findall(text)
    if matches:
        records.append(_record("phone", f"{matches[0]} (×{len(matches)})"))
    new_text = phone_re.sub("[PHONE-REDACTED]", text)
    return new_text, records


def redact_timestamps(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Replace specific timestamps with day-of-week or relative at T2+."""
    if target_tier < 2:
        return text, []
    records: list[dict] = []

    # ISO timestamps with time component (consume optional seconds + timezone suffix)
    iso_re = re.compile(r"\b(\d{4}-\d{2}-\d{2})[T\s]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?")

    def replace(m: re.Match) -> str:
        date_str = m.group(1)
        try:
            dt = datetime.fromisoformat(date_str)
            day = dt.strftime("%A").lower()
            return f"earlier ({day})"
        except ValueError:
            return m.group(0)

    matches = iso_re.findall(text)
    if matches:
        records.append(_record("timestamp_iso", f"{len(matches)} specific timestamp(s) → day-of-week"))
    new_text = iso_re.sub(replace, text)
    return new_text, records


def redact_internal_paths(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Replace internal infra paths at T2+."""
    if target_tier < 2:
        return text, []
    records: list[dict] = []
    new_text = text

    patterns = [
        (r"~/\.claude/[^\s`)\]]+", "claude_path"),
        (r"~/\.config/fpai/[^\s`)\]]+", "fpai_config_path"),
        (r"/Users/jamessunheart/[^\s`)\]]+", "absolute_user_path"),
    ]
    for regex_str, name in patterns:
        rx = re.compile(regex_str)
        matches = rx.findall(new_text)
        if matches:
            records.append(_record(f"internal_path_{name}", f"{matches[0][:40]}... (×{len(matches)})"))
            new_text = rx.sub("[INTERNAL-PATH]", new_text)

    return new_text, records


def redact_inflight_language(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Strip 'considering' / 'might pivot' / etc. at T2+."""
    if target_tier < 2:
        return text, []
    records: list[dict] = []
    inflight_phrases = [
        r"\bmight pivot\b",
        r"\bconsidering whether\b",
        r"\bin-flight (?:strategy|deliberation)\b",
        r"\bdeliberating on\b",
        r"\buncertain about\b",
    ]
    new_text = text
    for phrase_re in inflight_phrases:
        rx = re.compile(phrase_re, re.IGNORECASE)
        matches = rx.findall(new_text)
        if matches:
            records.append(_record("inflight_language", f"{matches[0]} (×{len(matches)}) → 'deliberation in progress'"))
            new_text = rx.sub("deliberation in progress", new_text)
    return new_text, records


# ---------------------------------------------------------------------------
# Voice + adversarial checks (Tier 3 only)
# ---------------------------------------------------------------------------

def voice_check(text: str) -> tuple[bool, list[str]]:
    """Return (passed, reasons_if_failed) — heuristic v0.1.

    Honest gap: real version needs LLM pass. v0.1 catches obvious leaks.
    """
    reasons = []

    # First-person James pronouns referring to private emotional state
    private_state_re = re.compile(
        r"\bI (?:feel|am feeling|am scared|am worried|am uncertain|don'?t know|am angry)\b",
        re.IGNORECASE,
    )
    if private_state_re.search(text):
        reasons.append("contains first-person private emotional state")

    # Remaining redaction markers after pipeline (incomplete redaction)
    if "[KEY-REDACTED]" in text or "[WALLET-REDACTED]" in text or "[IP-REDACTED]" in text:
        # These are OK to remain ONLY if they're standalone; flag if they appear inside flowing prose where they look weird
        # Heuristic: if a redaction marker appears WITHOUT a code-block or bracket nearby, it looks bad
        for marker in ["[KEY-REDACTED]", "[WALLET-REDACTED]", "[IP-REDACTED]"]:
            count = text.count(marker)
            if count > 3:
                reasons.append(f"too many {marker} markers ({count}) — content is redaction-heavy, consider abstracting instead")

    return (len(reasons) == 0, reasons)


def adversarial_check(text: str) -> tuple[bool, list[str]]:
    """Return (passed, reasons_if_failed) — heuristic v0.1."""
    reasons = []

    # Catch surviving exploitable patterns
    danger_patterns = [
        (r"\.token\b", "references token files"),
        (r"\.env\b", "references env files"),
        (r"\bssh\s+\w+@", "contains SSH command"),
        (r"\bpassword\s*[=:]\s*\S+", "contains password assignment"),
        (r"\bAPI[_\s]?KEY\s*[=:]\s*\S+", "contains API key assignment"),
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "contains surviving IP address (redaction failed)"),
    ]
    for pattern, reason in danger_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            reasons.append(reason)

    # Financial bait — surviving exact $ amounts (redaction should have caught)
    if re.search(r"\$\d+(?:,\d{3})*(?:\.\d+)?[kKmM]?\b", text):
        reasons.append("contains surviving exact dollar amount (redaction failed)")

    return (len(reasons) == 0, reasons)


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

REDACTION_ORDER = [
    redact_api_keys,         # do first (catch secrets before they get partially abstracted)
    redact_wallets,
    redact_ips,
    redact_emails,
    redact_phones,
    redact_dollar_amounts,
    redact_persons,
    redact_timestamps,
    redact_internal_paths,
    redact_inflight_language,
]


def transform(text: str, target_tier: int) -> tuple[str, list[dict]]:
    """Apply all redactions for the target tier. Return (new_text, audit_records)."""
    records: list[dict] = []
    current = text
    for fn in REDACTION_ORDER:
        current, new_records = fn(current, target_tier)
        records.extend(new_records)
    return current, records


def parse_frontmatter_classification(text: str) -> str:
    """Extract `classification:` value from yaml frontmatter. Default to PRIVATE."""
    fm_re = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
    m = fm_re.match(text)
    if not m:
        return "PRIVATE"
    fm = m.group(1)
    # Look for top-level classification field
    cls_re = re.compile(r"^classification:\s*([A-Z-]+)\s*$", re.MULTILINE)
    cls_m = cls_re.search(fm)
    if cls_m:
        val = cls_m.group(1).strip()
        if val in TIERS:
            return val
    return "PRIVATE"


def set_frontmatter_classification(text: str, new_classification: str) -> str:
    """Update or insert classification field in frontmatter."""
    if new_classification not in TIERS:
        raise ValueError(f"invalid classification: {new_classification}")

    fm_re = re.compile(r"^(---\n)(.*?)(\n---)", re.DOTALL)
    m = fm_re.match(text)
    if not m:
        # No frontmatter — prepend one
        return f"---\nclassification: {new_classification}\n---\n\n{text}"

    fm_body = m.group(2)
    cls_re = re.compile(r"^classification:\s*[A-Z-]+\s*$", re.MULTILINE)
    if cls_re.search(fm_body):
        new_fm_body = cls_re.sub(f"classification: {new_classification}", fm_body)
    else:
        new_fm_body = fm_body + f"\nclassification: {new_classification}"
    return m.group(1) + new_fm_body + m.group(3) + text[m.end():]


def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_audit(audit_dir: Path, record: dict) -> Path:
    """Append-only write of audit record."""
    audit_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_now().strftime("%Y%m%dT%H%M%SZ")
    basename = Path(record.get("source_path", "unknown")).stem
    out_path = audit_dir / f"{ts}_{basename}.json"
    # mode='x' → create-exclusive; never overwrite
    with open(out_path, "x") as f:
        json.dump(record, f, indent=2, default=str)
    return out_path


def check_tier3_published(hash_value: str, tier3_log: Path) -> bool:
    """Return True if hash already appears in the published Tier 3 log."""
    if not tier3_log.exists():
        return False
    with open(tier3_log) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[1] == hash_value:
                return True
    return False


def log_tier3_publish(tier3_log: Path, slug: str, hash_value: str, source_file: str) -> None:
    """Append-only log of every Tier 3 publish."""
    tier3_log.parent.mkdir(parents=True, exist_ok=True)
    ts = utc_now().isoformat()
    with open(tier3_log, "a") as f:
        f.write(f"{ts}\t{hash_value}\t{slug}\t{source_file}\n")
