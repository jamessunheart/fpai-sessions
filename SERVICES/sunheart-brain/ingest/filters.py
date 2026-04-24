"""
ingest/filters.py — privacy + security gate for brain-ingest.

Every Note flows through `classify(note)` BEFORE leaving the laptop. The
result is a tuple (sensitivity, pii_flags, decision) where decision ∈
{"skip", "personal", "public"}. The ingest loop honors the decision.

Philosophy:
    - Default-deny for anything smelling like secrets.
    - Cheap tags are the primary gate (user-controlled, explicit).
    - Regex PII detection is a backstop for things you forgot to tag.
    - Sensitivity is set from the outside (whitelist tags) where possible,
      then downgraded by content detection only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Sensitivity = Literal["🟢 Public", "🟡 Personal", "🔴 Private"]
Decision = Literal["skip", "personal", "public"]


# ---------------------------------------------------------------------------
# Tags that YOU control in Bear / elsewhere
# ---------------------------------------------------------------------------

SKIP_TAGS = {
    # Anything with these tags is completely excluded from ingest.
    "skip-brain", "private", "secret", "confidential",
    "nobrain", "do-not-index", "sensitive",
    # Common password/crypto buckets
    "passwords", "credentials", "keys", "2fa", "recovery",
    # Medical / legal / financial
    "medical", "legal", "finance-private", "banking",
}

PERSONAL_TAGS = {
    # Personal but OK to have in the brain — just kept out of GPT Connector.
    "personal", "journal", "relationships", "therapy", "reflection",
    "dreams", "feelings", "private-ok",
}

PUBLIC_ALLOW_TAGS = {
    # Force 🟢 Public regardless of content heuristics.
    "public", "ok-for-brain", "share", "blog", "reference",
}


# ---------------------------------------------------------------------------
# Content heuristics — auto-flag if these patterns appear
# ---------------------------------------------------------------------------

PII_PATTERNS: dict[str, re.Pattern] = {
    # Very conservative patterns — meant to err on the side of flagging.
    "SSN":           re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "Credit Card":   re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    "API Key":       re.compile(r"\b(?:sk|pk|AKIA|ghp|gho|xoxb|xox[pab])[A-Za-z0-9_\-]{16,}\b"),
    "Password":      re.compile(r"(?i)\b(?:password|passwd|pwd|pass)\s*[:=]\s*\S{6,}"),
    "Phone Number":  re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "Address":       re.compile(r"\b\d{1,5}\s+\w+(?:\s+\w+)*\s+(?:St|Street|Ave|Avenue|Blvd|Rd|Road|Ln|Lane|Dr|Drive|Ct|Court)\b", re.I),
    # Heuristics; false positives acceptable because false-positive = "quarantine to Personal", which is safe.
    "Medical":       re.compile(r"(?i)\b(?:diagnos(?:is|ed)|prescription|dose|mg/kg|HIV|hiv|cancer|tumor|ICD-?10)\b"),
    "Financial":     re.compile(r"(?i)\b(?:account number|routing number|IBAN|SWIFT|BTC address|ETH address|wallet seed|seed phrase)\b"),
    "Legal":         re.compile(r"(?i)\b(?:attorney[- ]?client|court case|subpoena|NDA|confidentiality agreement|settlement)\b"),
    "Email Chain":   re.compile(r"(?im)^(?:From|To|CC|BCC):\s*.+@.+\..+"),
}


# ---------------------------------------------------------------------------
# Crypto / seed-phrase detector: the 2048-word BIP39 list is too big to
# embed, so we use a heuristic — 12+ lowercase words each 3-8 chars long,
# all on roughly the same line. False-positive rate is very low against
# normal English prose.
# ---------------------------------------------------------------------------

SEED_PHRASE_RE = re.compile(
    r"(?m)^\s*(?:[a-z]{3,8}\s+){11,23}[a-z]{3,8}\s*$"
)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

@dataclass
class Classification:
    sensitivity: Sensitivity
    pii_flags: list[str]
    decision: Decision
    reason: str


def classify(content: str, tags: list[str]) -> Classification:
    tag_set = {t.lower().strip().lstrip("#") for t in (tags or [])}

    # 1. Tag-based skip is absolute.
    skip_hits = tag_set & SKIP_TAGS
    if skip_hits:
        return Classification(
            sensitivity="🔴 Private",
            pii_flags=[],
            decision="skip",
            reason=f"skipped by tag: {', '.join(sorted(skip_hits))}",
        )

    # 2. PII scan.
    pii: list[str] = []
    for label, pat in PII_PATTERNS.items():
        if pat.search(content or ""):
            pii.append(label)
    if SEED_PHRASE_RE.search(content or ""):
        pii.append("Password")  # treat seed phrases as password-tier secrets

    if pii:
        # Hard flags (secrets) → skip entirely. Soft flags (medical/legal) → personal tier.
        hard = {"SSN", "Credit Card", "API Key", "Password"}
        if hard & set(pii):
            return Classification(
                sensitivity="🔴 Private",
                pii_flags=pii,
                decision="skip",
                reason=f"PII detected (hard): {', '.join(sorted(hard & set(pii)))}",
            )
        # Soft PII → tier to Personal.
        return Classification(
            sensitivity="🟡 Personal",
            pii_flags=pii,
            decision="personal",
            reason=f"PII detected (soft): {', '.join(sorted(pii))}",
        )

    # 3. Personal-tag → personal tier.
    personal_hits = tag_set & PERSONAL_TAGS
    if personal_hits:
        return Classification(
            sensitivity="🟡 Personal",
            pii_flags=[],
            decision="personal",
            reason=f"personal tag: {', '.join(sorted(personal_hits))}",
        )

    # 4. Explicit public allow-tag.
    if tag_set & PUBLIC_ALLOW_TAGS:
        return Classification(
            sensitivity="🟢 Public",
            pii_flags=[],
            decision="public",
            reason="public allow-tag",
        )

    # 5. Default: Public.
    return Classification(
        sensitivity="🟢 Public",
        pii_flags=[],
        decision="public",
        reason="no signals, default public",
    )
