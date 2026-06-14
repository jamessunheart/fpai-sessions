"""
Receipt total + vendor + date extraction.

Three layers, falling through in order. The first layer that produces a
non-None amount wins. Each call returns a structured result with the method
used so the UI can show how the value was determined.

Layer 1 — caption (best-effort regex on the user's Telegram caption).
Layer 2 — OCR keyword scan (looks for TOTAL / GRAN TOTAL / AMOUNT DUE
          near a currency-prefixed number in Paperless OCR text).
Layer 3 — Ollama LLM (local, free) given the OCR + caption, asked to
          return a strict JSON {amount, currency, vendor, date, confidence}.

Costa Rica context: "₡" or "colones" → CRC, "$" or "USD" → USD.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from typing import Optional

import urllib.request

log = logging.getLogger("zv.parse_receipt")

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("ZV_RECEIPT_LLM_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = int(os.environ.get("ZV_RECEIPT_LLM_TIMEOUT", "60"))


# ─── result type ────────────────────────────────────────────────────────────
@dataclass
class ParsedReceipt:
    amount: Optional[float] = None
    currency: Optional[str] = None         # "USD" | "CRC" | "UNK"
    vendor: Optional[str] = None
    date: Optional[str] = None             # YYYY-MM-DD
    method: str = "none"                   # "caption" | "ocr_keyword" | "llm" | "none"
    confidence: float = 0.0
    raw_response: Optional[str] = None     # only set for LLM, debug aid

    def to_dict(self) -> dict:
        d = asdict(self)
        # Drop bulky raw_response unless caller wants it
        return d


# ─── Layer 1: caption regex ─────────────────────────────────────────────────
_CAPTION_RE = re.compile(
    r"(?P<sym>\$|₡|usd|crc|colon(?:es)?)\s*(?P<num>-?\d[\d.,]*)|"
    r"(?P<num2>-?\d[\d.,]*)\s*(?P<sym2>\$|₡|usd|crc|colon(?:es)?)",
    re.IGNORECASE,
)


def _parse_number(t: str) -> Optional[float]:
    t = (t or "").strip().replace(" ", "").replace("'", "")
    if not t:
        return None
    sign = -1 if t.startswith("-") else 1
    t = t.lstrip("+-")
    if "," in t and "." in t:
        if t.rfind(".") > t.rfind(","):
            t = t.replace(",", "")
        else:
            t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        parts = t.split(",")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            t = "".join(parts)
        else:
            t = t.replace(",", ".")
    try:
        return sign * float(t)
    except Exception:
        return None


def _normalise_currency(sym: str) -> str:
    s = (sym or "").lower()
    if "₡" in sym or "crc" in s or "colon" in s:
        return "CRC"
    if "$" in sym or "usd" in s or "dollar" in s:
        return "USD"
    return "UNK"


def parse_caption(caption: str) -> Optional[ParsedReceipt]:
    if not caption:
        return None
    text = caption.strip()
    # Skip pure command captions like "/receipt" with no content.
    body = re.sub(r"^/(receipt|proforma|acct)\b\s*", "", text, flags=re.IGNORECASE).strip()
    if not body:
        return None
    m = _CAPTION_RE.search(body)
    if not m:
        return None
    num_str = m.group("num") or m.group("num2") or ""
    sym = m.group("sym") or m.group("sym2") or ""
    amt = _parse_number(num_str)
    if amt is None:
        return None
    return ParsedReceipt(
        amount=abs(amt),
        currency=_normalise_currency(sym),
        vendor=_short_vendor_from_caption(body),
        method="caption",
        confidence=0.95,
    )


def _short_vendor_from_caption(caption: str) -> Optional[str]:
    # Strip leading currency token, then take the rest as vendor hint.
    s = re.sub(_CAPTION_RE, "", caption).strip(" -+,.;:")
    s = re.sub(r"\s+", " ", s)
    if not s:
        return None
    return s[:60]


# ─── Layer 2: OCR keyword scan ──────────────────────────────────────────────
# Receipts almost always label their final total with one of these keywords
# (Spanish/English; Costa Rica is bilingual on receipts). We score each
# candidate match and pick the highest-scoring one.

_TOTAL_KEYWORDS = [
    # (regex, score) — higher score = more authoritative
    (r"\bgran(?:\s+)?total\b", 100),
    (r"\btotal\s+a?\s*pagar\b", 100),
    (r"\btotal\s+general\b", 95),
    (r"\bamount\s+due\b", 95),
    (r"\bgrand\s+total\b", 95),
    (r"\btotal\s+final\b", 90),
    (r"\btotal\b", 60),
    (r"\bsubtotal\b", 30),  # weak — we'd rather skip and go to LLM
    (r"\btotal\s+factura\b", 90),
    (r"\bmonto\s+total\b", 85),
    (r"\bnet(?:o)?\s+a\s+pagar\b", 85),
]

_NUM_RE = re.compile(
    r"(?P<sym>\$|₡|usd|crc|colon(?:es)?)?\s*(?P<num>\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*(?P<sym2>\$|₡|usd|crc|colon(?:es)?)?",
    re.IGNORECASE,
)


def parse_ocr_keyword(ocr_text: str) -> Optional[ParsedReceipt]:
    if not ocr_text or len(ocr_text) < 10:
        return None
    text = ocr_text.replace("\u00a0", " ")
    # Find each keyword and the nearest number after it (within 60 chars).
    candidates: list[tuple[int, float, str]] = []  # (score, amount, currency)
    for kw_re, base_score in _TOTAL_KEYWORDS:
        for m in re.finditer(kw_re, text, flags=re.IGNORECASE):
            window = text[m.end(): m.end() + 80]
            num_m = _NUM_RE.search(window)
            if not num_m:
                continue
            amt = _parse_number(num_m.group("num"))
            if amt is None or amt <= 0:
                continue
            sym = num_m.group("sym") or num_m.group("sym2") or ""
            currency = _normalise_currency(sym)
            # Prefer matches with explicit currency symbol nearby.
            score = base_score + (10 if currency != "UNK" else 0)
            # Penalise tiny amounts (likely tax line, not total).
            if amt < 1:
                score -= 30
            candidates.append((score, amt, currency))

    if not candidates:
        return None

    # If we have multiple candidates, the highest-scoring + largest-amount wins.
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    score, amt, currency = candidates[0]
    confidence = min(0.85, 0.5 + score / 200.0)

    # Try to spot a vendor: usually the first non-empty line of the receipt.
    vendor = None
    for line in text.splitlines():
        line = line.strip()
        if line and len(line) > 3 and not re.match(r"^[\d\s.,/:-]+$", line):
            vendor = line[:60]
            break

    return ParsedReceipt(
        amount=amt,
        currency=currency,
        vendor=vendor,
        method="ocr_keyword",
        confidence=round(confidence, 2),
    )


# ─── Layer 3: Ollama LLM ────────────────────────────────────────────────────
_LLM_PROMPT = """You are extracting structured data from a Costa Rican receipt scanned by OCR. The OCR text may have errors. Return ONLY a JSON object with these keys, no prose:

{{
  "amount": <total amount as number, no currency symbol, decimal point only, null if unknown>,
  "currency": "USD" or "CRC" or "UNK",
  "vendor": <short merchant name, max 60 chars, null if unknown>,
  "date": "YYYY-MM-DD" or null,
  "confidence": <0.0 to 1.0>
}}

Rules:
- "₡" or "colones" or "CRC" means CRC. "$" or "USD" or "dollar" means USD.
- The total is the FINAL after-tax amount. Look for keywords: TOTAL, GRAN TOTAL, TOTAL A PAGAR, MONTO TOTAL, AMOUNT DUE, GRAND TOTAL.
- If multiple totals appear, pick the LARGEST (the after-tax/grand total, not subtotal).
- Vendor is usually the first business name at the top of the receipt.
- If OCR is unreadable, return amount: null, confidence: 0.0.
- Output JSON only, no markdown code fences, no commentary.

OCR TEXT:
<<<
{ocr}
>>>

USER CAPTION (Telegram, may include the amount explicitly):
<<<
{caption}
>>>
"""


def parse_with_llm(ocr_text: str, caption: str = "", model: str = OLLAMA_MODEL,
                   timeout: int = OLLAMA_TIMEOUT) -> Optional[ParsedReceipt]:
    if not (ocr_text or caption):
        return None
    prompt = _LLM_PROMPT.format(ocr=(ocr_text or "")[:6000], caption=(caption or "")[:500])
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "top_p": 0.9, "num_predict": 256},
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning("Ollama call failed: %s", e)
        return None

    raw = (data.get("response") or "").strip()
    # Strip any accidental markdown fence
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"```$", "", raw).strip()
    try:
        parsed = json.loads(raw)
    except Exception as e:
        log.warning("LLM response not JSON: %s ; raw=%r", e, raw[:200])
        return ParsedReceipt(method="llm", confidence=0.0, raw_response=raw[:1000])

    amt = parsed.get("amount")
    if amt is not None:
        try:
            amt = float(amt)
            if amt <= 0:
                amt = None
        except Exception:
            amt = None
    cur = (parsed.get("currency") or "").upper().strip()
    if cur not in ("USD", "CRC", "UNK"):
        cur = "UNK"
    vendor = parsed.get("vendor")
    if vendor:
        vendor = str(vendor)[:60]
    date_s = parsed.get("date")
    if date_s and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_s)):
        date_s = None
    conf = parsed.get("confidence")
    try:
        conf = float(conf)
    except Exception:
        conf = 0.5 if amt is not None else 0.0

    return ParsedReceipt(
        amount=amt,
        currency=cur if amt is not None else None,
        vendor=vendor,
        date=date_s,
        method="llm",
        confidence=round(conf, 2),
        raw_response=raw[:1000],
    )


# ─── Orchestrator ───────────────────────────────────────────────────────────
def parse_one(*, caption: str = "", ocr_text: str = "",
              use_llm: bool = True) -> ParsedReceipt:
    """Run all three layers and return the best result."""
    # 1. Caption
    cap_result = parse_caption(caption)
    if cap_result and cap_result.amount:
        return cap_result

    # 2. OCR keyword
    ocr_result = parse_ocr_keyword(ocr_text)

    # 3. LLM — only if (a) enabled, and (b) OCR keyword didn't already give us
    # a high-confidence match. The LLM is more accurate but ~3-10s per call.
    if use_llm and (not ocr_result or ocr_result.confidence < 0.8):
        llm_result = parse_with_llm(ocr_text, caption)
        if llm_result and llm_result.amount:
            # Prefer LLM over OCR keyword if both produced an amount.
            return llm_result

    if ocr_result and ocr_result.amount:
        return ocr_result

    if cap_result:  # caption with vendor but no amount
        return cap_result

    return ParsedReceipt(method="none", confidence=0.0)


# ─── CLI for ad-hoc testing ─────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Test the receipt parser.")
    p.add_argument("--caption", default="")
    p.add_argument("--ocr", default="")
    p.add_argument("--ocr-file", default="")
    p.add_argument("--no-llm", action="store_true")
    args = p.parse_args()
    ocr = args.ocr
    if args.ocr_file:
        ocr = open(args.ocr_file).read()
    res = parse_one(caption=args.caption, ocr_text=ocr, use_llm=not args.no_llm)
    print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
