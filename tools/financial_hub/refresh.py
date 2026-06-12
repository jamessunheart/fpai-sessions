#!/usr/bin/env python3
"""
Financial Hub refresh.

Reads local/vault financial sources as DATA and writes a secret-free Obsidian
summary. It does not move money, decrypt secrets, call APIs, or write raw
account/venue line items into the vault output.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HOME = Path.home()
VAULT = Path(os.environ.get(
    "FPAI_VAULT",
    HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS",
))
CONFIG = Path(os.environ.get("FPAI_CONFIG", HOME / ".config" / "fpai"))

TREASURY_DIR = CONFIG / "treasury"
COST_LEDGER = CONFIG / "cost" / "ledger.jsonl"
SOL_LIVE = CONFIG / "sol_live" / "latest.json"

CURRENT_RESOURCES = TREASURY_DIR / "CURRENT_RESOURCES_2026-06-03.md"
TREASURY_CACHE = TREASURY_DIR / "CURRENT.md"

ZEN_ACCOUNTING = VAULT / "00_MEMORY" / "ZEN VILLAGE ACCOUNTING.md"
TREASURY_TODAY = VAULT / "00_MEMORY" / "TREASURY TODAY.md"
OUTPUT = VAULT / "00_MEMORY" / "FINANCIAL HUB.md"


@dataclass
class ResourceSummary:
    source: str
    cash_usd: float | None = None
    crypto_usd: float | None = None
    bullion_usd: float | None = None
    liability_usd: float | None = None
    net_spendable_usd: float | None = None
    net_worth_usd: float | None = None
    reconciliation: list[str] | None = None


def read(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""


def money_to_float(raw: str) -> float | None:
    raw = raw.strip().replace(",", "").replace("~", "")
    raw = raw.replace("$", "").replace("≈", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not m:
        return None
    return float(m.group(0))


def round_money(value: float | None, nearest: int = 100) -> str:
    if value is None:
        return "unknown"
    rounded = round(value / nearest) * nearest
    if abs(rounded) >= 1000:
        return f"~${rounded/1000:.0f}k"
    return f"~${rounded:,.0f}"


def pct(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.1f}%"


def extract_first_money(text: str, patterns: Iterable[str]) -> float | None:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I | re.S)
        if m:
            val = money_to_float(m.group(1))
            if val is not None:
                return val
    return None


def parse_resources() -> ResourceSummary:
    text = read(CURRENT_RESOURCES)
    if not text:
        return ResourceSummary(source=str(CURRENT_RESOURCES), reconciliation=["Missing current resources snapshot."])
    treasury_today = read(TREASURY_TODAY)

    cash = extract_first_money(text, [r"\*\*Subtotal cash\*\*\s*\|\s*\*\*~?([\d,.$]+)\*\*"])
    crypto = extract_first_money(text, [r"\*\*Subtotal crypto\*\*\s*\|\s*\*\*~?([\d,.$]+)"])
    bullion = extract_first_money(text, [r"Silver:.*?\*\*\$?([\d,.$]+)\*\*"])
    liquid = extract_first_money(text, [r"LIQUID \+ crypto \+ silver:\s*~?\$?([\d,.]+)"])
    liability = extract_first_money(text, [r"Credit Card:\s*\$?([\d,.]+)"])
    net = liquid - liability if liquid is not None and liability is not None else liquid
    net_worth = extract_first_money(text, [r"Net worth \(rough\):\s*~?\$?([\d,.]+)M"])
    if net_worth is not None:
        net_worth *= 1_000_000

    rec = []
    if "## 🟡 Reconciliation questions" in text:
        seg = text.split("## 🟡 Reconciliation questions", 1)[1]
        for line in seg.splitlines():
            m = re.match(r"\d+\.\s+(.+)", line.strip())
            if m:
                rec.append(re.sub(r"\s+", " ", m.group(1)).strip())
    if "RESOLVED" in treasury_today and "Bitrue $62,775" in treasury_today:
        rec = [item for item in rec if not item.startswith("Bitrue $62,775")]
    return ResourceSummary(
        source=str(CURRENT_RESOURCES),
        cash_usd=cash,
        crypto_usd=crypto,
        bullion_usd=bullion,
        liability_usd=liability,
        net_spendable_usd=net,
        net_worth_usd=net_worth,
        reconciliation=rec[:5],
    )


def parse_burn() -> dict[str, float | None]:
    text = read(TREASURY_CACHE)
    recurring = extract_first_money(text, [r"RECURRING TOTAL\*\*\s*\|\s*\*\*\$?([\d,.]+)k/mo"])
    active = extract_first_money(text, [r"TOTAL while Dragon Stage active\*\*\s*\|\s*\*\*\$?([\d,.]+)k/mo"])
    post = extract_first_money(text, [r"Recurring post-Dragon-Stage\*\*\s*\|\s*\*\*\$?([\d,.]+)k/mo"])
    # Values in the cache table are rendered as k/mo.
    return {
        "recurring": recurring * 1000 if recurring is not None else None,
        "dragon_active": active * 1000 if active is not None else None,
        "post_dragon": post * 1000 if post is not None else None,
    }


def parse_sol() -> dict[str, object]:
    try:
        data = json.loads(read(SOL_LIVE))
    except Exception:
        return {"available": False}
    totals = data.get("totals") or {}
    longs = data.get("longs") or []
    return {
        "available": True,
        "fetched_at": data.get("fetched_at"),
        "sol_usd": data.get("sol_usd"),
        "equity": totals.get("equity_now_usd"),
        "invested": totals.get("invested_usd"),
        "pnl": totals.get("unrealized_pnl"),
        "notional": totals.get("notional_usd"),
        "min_liq_distance_pct": totals.get("min_liq_distance_pct"),
        "liq_levels": [x.get("liq") for x in longs if x.get("liq") is not None],
        "source": data.get("source"),
    }


def parse_costs(now: dt.datetime) -> dict[str, float]:
    totals = {
        "today_metered": 0.0,
        "today_shadow": 0.0,
        "week_metered": 0.0,
        "week_shadow": 0.0,
    }
    today = now.date()
    week_start = today - dt.timedelta(days=6)
    for line in read(COST_LEDGER).splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            ts = dt.datetime.fromisoformat(row["timestamp"]).date()
        except Exception:
            continue
        usd = float(row.get("est_usd") or 0)
        billing = str(row.get("billing") or "")
        is_metered = "metered" in billing and "shadow" not in billing
        if ts == today:
            totals["today_metered" if is_metered else "today_shadow"] += usd
        if week_start <= ts <= today:
            totals["week_metered" if is_metered else "week_shadow"] += usd
    return totals


def parse_zen() -> dict[str, str]:
    text = read(ZEN_ACCOUNTING)
    out = {
        "balance": "unknown",
        "period_outflow": "unknown",
        "posture": "unknown",
    }
    m = re.search(r"Current balance:.*?\*\*([^*]+)\*\*\s*\(~\$?([\d,.]+)\)", text)
    if m:
        out["balance"] = f"~${money_to_float(m.group(2)) or 0:,.0f}"
    m = re.search(r"TOTAL OUTFLOW.*?\*\*~₡([^*]+)\*\*\s*\|\s*~\$?([\d,.]+)", text)
    if m:
        out["period_outflow"] = f"~${money_to_float(m.group(2)) or 0:,.0f}"
    if "construction-heavy" in text:
        out["posture"] = "construction-heavy period; book project surge separately from recurring ops"
    return out


SECRET_PATTERNS = [
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\b\s*[:=]", re.I),
    re.compile(r"\b(?:0x[a-fA-F0-9]{20,}|[13][a-km-zA-HJ-NP-Z1-9]{25,}|bc1[a-zA-HJ-NP-Z0-9]{25,})\b"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
]


def leak_findings(text: str) -> list[str]:
    findings = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(pattern.pattern)
    return findings


def render(now: dt.datetime) -> str:
    resources = parse_resources()
    burn = parse_burn()
    sol = parse_sol()
    costs = parse_costs(now)
    zen = parse_zen()
    rec = resources.reconciliation or []

    sol_line = "not available"
    if sol.get("available"):
        liq_levels = [x for x in sol.get("liq_levels", []) if x is not None]
        liq = f"liq ~${min(liq_levels):.0f}" if liq_levels else "liq unknown"
        sol_line = (
            f"{round_money(sol.get('equity'), 100)} equity · "
            f"{round_money(sol.get('pnl'), 100)} unrealized P/L · "
            f"{liq} · {pct(sol.get('min_liq_distance_pct'))} away"
        )

    lines = [
        "# 💰 FINANCIAL HUB",
        "",
        "*Secret-free consolidated view. Exact balances, wallet addresses, keys, and account details stay local/encrypted.*",
        f"*Refreshed: {now.strftime('%Y-%m-%d %H:%M %Z')} · source: `tools/financial_hub/refresh.py`*",
        "",
        "## 10-second read",
        "",
        f"- **Net spendable:** {round_money(resources.net_spendable_usd, 1000)} · pending reconciliation",
        f"- **Split:** cash {round_money(resources.cash_usd, 1000)} · crypto {round_money(resources.crypto_usd, 1000)} · bullion {round_money(resources.bullion_usd, 1000)}",
        f"- **Burn:** recurring {round_money(burn.get('recurring'), 100)} / mo · Dragon-active {round_money(burn.get('dragon_active'), 100)} / mo",
        f"- **SOL monitor:** {sol_line}",
        f"- **Zen Village:** wallet {zen['balance']} · recent period outflow {zen['period_outflow']} · {zen['posture']}",
        f"- **AI costs:** metered today ${costs['today_metered']:.2f} · metered 7d ${costs['week_metered']:.2f} · flat-plan shadow 7d ${costs['week_shadow']:.0f}",
        "",
        "## Buckets",
        "",
        "| Bucket | Picture | Current read |",
        "|---|---|---|",
        f"| Spendable | cash + crypto + bullion, minus obvious liability | {round_money(resources.net_spendable_usd, 1000)} |",
        f"| Idle / yield opportunity | cash + TRUST idle remain the obvious sure-win path | see [[TREASURY TODAY]] |",
        f"| Burn | recurring vs Dragon Stage project surge | {round_money(burn.get('recurring'), 100)} recurring · {round_money(burn.get('dragon_active'), 100)} active |",
        f"| Open position risk | SOL 3x long monitor only; do not double-count inside Bitrue | {sol_line} |",
        f"| Zen Village ops | pass-through ops/construction wallet | {zen['posture']} |",
        f"| AI cost discipline | $20/day cap applies to metered APIs only | today metered ${costs['today_metered']:.2f} |",
        "",
        "## Open reconciliation",
        "",
    ]
    if rec:
        lines.extend(f"- {item}" for item in rec)
    else:
        lines.append("- No current reconciliation questions found.")

    lines.extend([
        "",
        "## Source map",
        "",
        f"- Local latest resources: `{resources.source}`",
        f"- Local live SOL: `{SOL_LIVE}`",
        f"- Local AI cost ledger: `{COST_LEDGER}`",
        "- Vault summary: [[TREASURY TODAY]]",
        "- Vault ops: [[ZEN VILLAGE ACCOUNTING]]",
        "- Encrypted detail: [[SENSITIVE RESOURCES (encrypted)]] / `RESOURCES_SENSITIVE.md.gpg`",
        "",
        "## Guardrails",
        "",
        "- Summary only: no account-by-account table, no addresses, no keys.",
        "- Read-only: this script never moves funds, deploys yield, or opens encrypted resources.",
        "- Any money movement still needs James's explicit, specific approval.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the secret-free Financial Hub note.")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check-only", action="store_true", help="Render and leak-check without writing.")
    args = parser.parse_args()

    now = dt.datetime.now().astimezone()
    text = render(now)
    findings = leak_findings(text)
    if findings:
        print("leak_check=fail")
        for finding in findings:
            print(f"pattern={finding}")
        return 2
    if args.check_only:
        print("leak_check=pass")
        print(f"bytes={len(text.encode('utf-8'))}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(f"wrote={args.output}")
    print("leak_check=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
