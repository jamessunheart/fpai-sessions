#!/usr/bin/env python3
"""Compare live Sweep Signal audit rows against paper trades."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class Trade:
    source: str
    symbol: str
    side: str
    entry_ts: str
    exit_ts: str | None
    entry_price: float | None
    exit_price: float | None
    pnl: float
    raw: dict[str, Any]

    @property
    def key(self) -> tuple[str, str]:
        return (self.symbol, self.side)


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_rows(path: Path, source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        row["_source"] = source
        rows.append(row)
    return rows


def row_ts(row: dict[str, Any]) -> str:
    return str(row.get("ts") or row.get("timestamp") or row.get("time") or "")


def row_symbol(row: dict[str, Any]) -> str:
    return str(row.get("symbol") or row.get("sym") or row.get("coin") or "").upper()


def row_side(row: dict[str, Any]) -> str:
    side = str(row.get("side") or row.get("direction") or row.get("dir") or "").lower()
    if side in {"buy", "long"}:
        return "long"
    if side in {"sell", "short"}:
        return "short"
    return side


def build_trades(rows: list[dict[str, Any]], source: str) -> list[Trade]:
    open_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    trades: list[Trade] = []
    for row in rows:
        phase = str(row.get("phase") or row.get("event") or "").lower()
        symbol = row_symbol(row)
        side = row_side(row)
        if not symbol or not side:
            continue
        key = (symbol, side)
        if phase in {"entry", "entry_filled", "filled", "open"}:
            open_by_key[key] = row
        elif phase in {"exit", "stop_hit", "target_hit", "closed", "close"}:
            entry = open_by_key.pop(key, {})
            trades.append(
                Trade(
                    source=source,
                    symbol=symbol,
                    side=side,
                    entry_ts=row_ts(entry) or row_ts(row),
                    exit_ts=row_ts(row),
                    entry_price=parse_float(entry.get("price") or entry.get("entry") or entry.get("entry_price")),
                    exit_price=parse_float(row.get("price") or row.get("exit") or row.get("exit_price")),
                    pnl=parse_float(row.get("realized_pnl") or row.get("pnl") or row.get("profit")) or 0.0,
                    raw=row,
                )
            )
    for key, entry in open_by_key.items():
        symbol, side = key
        trades.append(
            Trade(
                source=source,
                symbol=symbol,
                side=side,
                entry_ts=row_ts(entry),
                exit_ts=None,
                entry_price=parse_float(entry.get("price") or entry.get("entry") or entry.get("entry_price")),
                exit_price=None,
                pnl=parse_float(entry.get("realized_pnl") or entry.get("pnl")) or 0.0,
                raw=entry,
            )
        )
    return trades


def ts_value(value: str | None) -> float:
    if not value:
        return 0.0
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def pair_trades(live: list[Trade], paper: list[Trade]) -> list[tuple[Trade | None, Trade | None]]:
    remaining = list(paper)
    pairs: list[tuple[Trade | None, Trade | None]] = []
    for live_trade in live:
        candidates = [trade for trade in remaining if trade.key == live_trade.key]
        if candidates:
            best = min(candidates, key=lambda trade: abs(ts_value(trade.entry_ts) - ts_value(live_trade.entry_ts)))
            remaining.remove(best)
            pairs.append((live_trade, best))
        else:
            pairs.append((live_trade, None))
    for paper_trade in remaining:
        pairs.append((None, paper_trade))
    return pairs


def max_drawdown(pnls: list[float]) -> float:
    peak = 0.0
    equity = 0.0
    worst = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return worst


def aggregate(trades: list[Trade]) -> dict[str, Any]:
    closed = [trade for trade in trades if trade.exit_ts]
    pnls = [trade.pnl for trade in closed]
    wins = [pnl for pnl in pnls if pnl > 0]
    return {
        "trades": len(closed),
        "pnl": sum(pnls),
        "win_rate": (len(wins) / len(pnls) * 100) if pnls else 0.0,
        "avg_pnl": mean(pnls) if pnls else 0.0,
        "drawdown": max_drawdown(pnls),
    }


def render_report(live_path: Path, paper_path: Path) -> str:
    live = build_trades(parse_rows(live_path, "live"), "live")
    paper = build_trades(parse_rows(paper_path, "paper"), "paper")
    pairs = pair_trades(live, paper)
    live_agg = aggregate(live)
    paper_agg = aggregate(paper)

    lines = [
        "# Whaletrack Verdict",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Live audit: `{live_path}`",
        f"Paper audit: `{paper_path}`",
        "",
        "## Aggregate",
        "",
        "| Stream | Closed trades | PnL | Win rate | Avg PnL | Max drawdown |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Live actual | {live_agg['trades']} | {live_agg['pnl']:.2f} | {live_agg['win_rate']:.1f}% | {live_agg['avg_pnl']:.2f} | {live_agg['drawdown']:.2f} |",
        f"| Paper would-have | {paper_agg['trades']} | {paper_agg['pnl']:.2f} | {paper_agg['win_rate']:.1f}% | {paper_agg['avg_pnl']:.2f} | {paper_agg['drawdown']:.2f} |",
        f"| Delta live-paper |  | {live_agg['pnl'] - paper_agg['pnl']:.2f} | {live_agg['win_rate'] - paper_agg['win_rate']:.1f} pp | {live_agg['avg_pnl'] - paper_agg['avg_pnl']:.2f} | {live_agg['drawdown'] - paper_agg['drawdown']:.2f} |",
        "",
        "## Per-Trade Join",
        "",
        "| Symbol | Side | Live entry | Live PnL | Paper entry | Paper PnL | Slippage/Delta |",
        "|---|---|---|---:|---|---:|---:|",
    ]
    for live_trade, paper_trade in pairs:
        symbol = (live_trade or paper_trade).symbol if (live_trade or paper_trade) else ""
        side = (live_trade or paper_trade).side if (live_trade or paper_trade) else ""
        live_entry = live_trade.entry_ts if live_trade else "missing"
        paper_entry = paper_trade.entry_ts if paper_trade else "missing"
        live_pnl = live_trade.pnl if live_trade else 0.0
        paper_pnl = paper_trade.pnl if paper_trade else 0.0
        lines.append(
            f"| {symbol} | {side} | {live_entry} | {live_pnl:.2f} | {paper_entry} | {paper_pnl:.2f} | {live_pnl - paper_pnl:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Join key is symbol + side, paired by nearest entry timestamp.",
            "- Missing live rows indicate paper trades that never executed live; missing paper rows indicate live-only execution.",
            "- This tool reads local JSONL files only. It does not call Hyperliquid and cannot move funds.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", required=True, type=Path)
    parser.add_argument("--paper", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = render_report(args.live, args.paper)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
