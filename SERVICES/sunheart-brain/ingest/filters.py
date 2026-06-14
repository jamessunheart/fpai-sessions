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
    "keyinfo", "key-info",  # vault / credentials bucket (Bear tag)
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
    "API Key":       re.compile(
        r"\b(?:sk|pk|AKIA|ghp|gho|xoxb|xox[pab]|AIza|ya29|rk_live|sk_live|"
        r"sk_test|pk_test|glpat|Bearer\s+[A-Za-z0-9_\-]+|eyJ[A-Za-z0-9_\-]{20,})"
        r"[A-Za-z0-9_\-\.]{16,}\b"
    ),
    "Password":      re.compile(r"(?i)(?:^|\b)(?:password|passwd|pwd|pass|secret|token)\s*[:=]\s*\S{6,}"),
    "Private Key":   re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |PGP |DSA )?PRIVATE KEY-----"),
    "URL Creds":     re.compile(r"\b[a-z]+://[^/\s:]+:[^/\s@]+@\S+", re.I),
    "Phone Number":  re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "Address":       re.compile(r"\b\d{1,5}\s+\w+(?:\s+\w+)*\s+(?:St|Street|Ave|Avenue|Blvd|Rd|Road|Ln|Lane|Dr|Drive|Ct|Court)\b", re.I),
    # Heuristics; false positives acceptable because false-positive = "quarantine to Personal", which is safe.
    "Medical":       re.compile(r"(?i)\b(?:diagnos(?:is|ed)|prescription|dose|mg/kg|HIV|hiv|cancer|tumor|ICD-?10)\b"),
    "Financial":     re.compile(
        r"(?i)\b(?:account number|routing number|IBAN|SWIFT|"
        r"BTC address|ETH address|wallet seed|seed phrase|private key|mnemonic|"
        r"0x[a-fA-F0-9]{40}|bc1[a-z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"
    ),
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


def classify(
    content: str,
    tags: list[str],
    default_sensitivity: Sensitivity = "🟢 Public",
) -> Classification:
    """Classify a note.

    `default_sensitivity` sets the floor for untagged/low-signal notes.
    Bear should pass "🟡 Personal" so any note without an explicit #public tag
    stays out of the GPT Connector and OpenAI embeddings until you review it.
    """
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
        hard = {"SSN", "Credit Card", "API Key", "Password", "Private Key", "URL Creds"}
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

    # 5. Default — caller-supplied floor.
    if default_sensitivity == "🟡 Personal":
        return Classification(
            sensitivity="🟡 Personal",
            pii_flags=[],
            decision="personal",
            reason="no signals, default personal (caller-supplied floor)",
        )
    return Classification(
        sensitivity="🟢 Public",
        pii_flags=[],
        decision="public",
        reason="no signals, default public",
    )
