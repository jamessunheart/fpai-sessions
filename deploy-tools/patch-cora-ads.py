#!/usr/bin/env python3
"""Patch CORA's build_context to include ad pipeline performance data."""

CORA_FILE = "/opt/fpai/cora-loop/agents/cora.py"

AD_BLOCK = '''
    # Read ad pipeline performance metrics
    try:
        import sqlite3 as _sql3
        adb = _sql3.connect("/opt/fpai/memory-bus/bus.db")
        adb.row_factory = _sql3.Row

        ad_msg = adb.execute(
            "SELECT content FROM messages WHERE type = ? AND to_agent IN (?, ?) ORDER BY created_at DESC LIMIT 1",
            ("ad_performance", "cora", "all")
        ).fetchone()
        if ad_msg:
            import json as _json
            ad_data = _json.loads(ad_msg["content"])
            parts.append("AD PIPELINE STATUS:")
            if ad_data.get("status") == "no_accounts":
                parts.append("  WARNING: " + ad_data.get("message", "No ad accounts connected"))
            else:
                perf = ad_data.get("performance", {})
                budget = ad_data.get("budget", {})
                parts.append("  Account: {} ({})".format(ad_data.get("account", "N/A"), ad_data.get("account_status", "?")))
                parts.append("  Active campaigns: {}".format(ad_data.get("campaigns_active", 0)))
                parts.append("  Daily spend rate: ${}/day".format(ad_data.get("daily_spend_rate", 0)))
                if perf:
                    parts.append("  Impressions: {} | Clicks: {} | CTR: {}%".format(perf.get("impressions", 0), perf.get("clicks", 0), perf.get("ctr", 0)))
                    parts.append("  Spend: ${} | Leads: {} | CPL: ${}".format(perf.get("spend", 0), perf.get("leads", 0), perf.get("cpl", 0)))
                    lc = perf.get("link_clicks", 0)
                    if lc > 0:
                        parts.append("  Link clicks to assessment: {}".format(lc))
                    opt = perf.get("optimization_actions", [])
                    if opt:
                        parts.append("  Auto-optimization actions: {}".format(len(opt)))
                        for a in opt[:3]:
                            parts.append("    -> {}".format(a))
                if budget:
                    remaining = budget.get("remaining")
                    if remaining is not None:
                        parts.append("  Budget remaining: ${}".format(remaining))
                    if ad_data.get("budget_alert"):
                        parts.append("  LOW BUDGET ALERT: Sunheart needs to top up Meta ad account")
            parts.append("")

        try:
            metrics = adb.execute(
                "SELECT date, impressions, clicks, ctr, spend, leads, cpl FROM ad_metrics ORDER BY date DESC LIMIT 7"
            ).fetchall()
            if metrics:
                parts.append("AD PERFORMANCE TREND (last 7 days):")
                total_spend = 0
                total_leads = 0
                total_clicks = 0
                for m in reversed(metrics):
                    parts.append("  {}: {} imp, {} clicks, CTR {}%, ${} spent, {} leads".format(
                        m["date"], m["impressions"], m["clicks"], m["ctr"], m["spend"], m["leads"]))
                    total_spend += m["spend"]
                    total_leads += m["leads"]
                    total_clicks += m["clicks"]
                parts.append("  7-day totals: ${:.2f} spent, {} clicks, {} leads".format(total_spend, total_clicks, total_leads))
                if total_leads > 0:
                    parts.append("  7-day avg CPL: ${:.2f}".format(total_spend / total_leads))
                parts.append("")
        except Exception:
            pass

        adb.close()
    except Exception:
        pass

'''

with open(CORA_FILE) as f:
    code = f.read()

MARKER = "    # Read gap analysis"
if MARKER in code:
    if "AD PIPELINE STATUS" not in code:
        code = code.replace(MARKER, AD_BLOCK + MARKER)
        with open(CORA_FILE, "w") as f:
            f.write(code)
        print("SUCCESS: CORA patched with ad performance reading")
    else:
        print("SKIP: Ad performance reading already present in CORA")
else:
    ALT = '    parts.append("Generate your strategic directive'
    if ALT in code and "AD PIPELINE STATUS" not in code:
        code = code.replace(ALT, AD_BLOCK + ALT)
        with open(CORA_FILE, "w") as f:
            f.write(code)
        print("SUCCESS: CORA patched (alternate marker)")
    else:
        print("ERROR: Could not find insertion point or already patched")
