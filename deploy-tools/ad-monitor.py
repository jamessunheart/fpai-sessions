#!/usr/bin/env python3
"""
Meta Ads Performance Monitor
Runs daily via systemd timer. Pulls campaign metrics, writes to bus,
auto-optimizes underperformers, alerts on low budget.
"""

import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BUS_DB = "/opt/fpai/memory-bus/bus.db"
LOG_DIR = "/opt/fpai/logs"
LOG_FILE = f"{LOG_DIR}/ad-monitor.log"
ENV_FILE = "/opt/fpai/cora-loop/.env"

GRAPH_API = "https://graph.facebook.com/v19.0"

TARGETING_CONFIG = "/opt/fpai/ad-monitor/targeting-config.json"

META_TOKEN = ""
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
AD_ACCOUNT_ID = ""

BUDGET_ALERT_THRESHOLDS = [50, 20]
CPL_PAUSE_MULTIPLIER = 2.0
MIN_DAYS_DATA = 3
MIN_SPEND_TO_JUDGE = 5.0


def load_env():
    global META_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, AD_ACCOUNT_ID
    envs = {}
    for ef in [ENV_FILE, "/opt/fpai/openclaw/workspace/.env"]:
        if os.path.exists(ef):
            with open(ef) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        envs[k.strip()] = v.strip().strip('"').strip("'")
    META_TOKEN = envs.get("META_TOKEN", os.environ.get("META_TOKEN", ""))
    TELEGRAM_BOT_TOKEN = envs.get("TELEGRAM_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    TELEGRAM_CHAT_ID = envs.get("TELEGRAM_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", ""))
    AD_ACCOUNT_ID = envs.get("META_AD_ACCOUNT_ID", os.environ.get("META_AD_ACCOUNT_ID", ""))

    if not META_TOKEN:
        META_TOKEN = "EAARD6gE7ftIBQpXI0m9sqoVgXNWLRvozSsKNfWzQfQvTZAWGK42yjNI3VgzPvdGaxlFCZBzoAepWz7LuWq4Dre9F8NNaUQZBljZBLo8SllgoVlxvIXwe7X48fBHPyWYtBCanmTvbeYXZBqJq2n0mFxJwN1mEYtWwly5dGPHR11AF8pouOymYloKXnMp36O0xw0QZDZD"

    load_config()


def load_config():
    global BUDGET_ALERT_THRESHOLDS, CPL_PAUSE_MULTIPLIER, MIN_DAYS_DATA, MIN_SPEND_TO_JUDGE
    if os.path.exists(TARGETING_CONFIG):
        try:
            with open(TARGETING_CONFIG) as f:
                cfg = json.load(f)
            ba = cfg.get("budget_alerts", {})
            BUDGET_ALERT_THRESHOLDS = ba.get("thresholds", BUDGET_ALERT_THRESHOLDS)
            opt = cfg.get("optimization", {})
            CPL_PAUSE_MULTIPLIER = opt.get("pause_if_cpl_multiplier", CPL_PAUSE_MULTIPLIER)
            MIN_DAYS_DATA = opt.get("min_days_data", MIN_DAYS_DATA)
            MIN_SPEND_TO_JUDGE = opt.get("min_spend_to_judge", MIN_SPEND_TO_JUDGE)
        except Exception:
            pass


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] [AD-MONITOR] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def meta_api(endpoint, method="GET", data=None):
    sep = "&" if "?" in endpoint else "?"
    url = f"{GRAPH_API}{endpoint}{sep}access_token={META_TOKEN}"
    req = urllib.request.Request(url, method=method)
    if data:
        req.data = urllib.parse.urlencode(data).encode()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except Exception:
            return {"error": {"message": f"HTTP {e.code}: {body[:200]}"}}
    except Exception as e:
        return {"error": {"message": str(e)}}


def tg_notify(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }).encode()
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception:
        pass


def bus_write(from_agent, to_agent, msg_type, content, priority="medium", thread_id=None):
    import uuid
    db = sqlite3.connect(BUS_DB)
    now = datetime.now(timezone.utc).isoformat()
    msg_id = str(uuid.uuid4())[:12]
    db.execute(
        "INSERT INTO messages (id, from_agent, to_agent, type, timestamp, content, priority, thread_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (msg_id, from_agent, to_agent, msg_type, now, json.dumps(content), priority, thread_id, now)
    )
    db.commit()
    db.close()
    return msg_id


def get_ad_accounts():
    result = meta_api("/me/adaccounts?fields=id,name,account_status,balance,amount_spent,currency,spend_cap")
    if "error" in result:
        log(f"Error fetching ad accounts: {result['error'].get('message', '?')}")
        return []
    return result.get("data", [])


def get_account_insights(account_id, days=1):
    fields = "impressions,reach,clicks,ctr,cpc,cpm,spend,actions,cost_per_action_type"
    result = meta_api(f"/{account_id}/insights?date_preset=last_{days}d&fields={fields}&level=account")
    if "error" in result:
        log(f"Error fetching insights for {account_id}: {result['error'].get('message', '?')}")
        return None
    data = result.get("data", [])
    return data[0] if data else None


def get_adset_insights(account_id, days=None):
    if days is None:
        days = MIN_DAYS_DATA
    fields = "adset_id,adset_name,impressions,clicks,ctr,spend,actions,cost_per_action_type"
    result = meta_api(f"/{account_id}/insights?date_preset=last_{days}d&fields={fields}&level=adset")
    if "error" in result:
        log(f"Error fetching ad set insights: {result['error'].get('message', '?')}")
        return []
    return result.get("data", [])


def get_active_campaigns(account_id):
    result = meta_api(f"/{account_id}/campaigns?fields=id,name,status,daily_budget&effective_status=[%22ACTIVE%22,%22PAUSED%22]")
    if "error" in result:
        return []
    return result.get("data", [])


def check_budget(account_id):
    result = meta_api(f"/{account_id}?fields=balance,amount_spent,spend_cap,currency")
    if "error" in result:
        return None
    balance = float(result.get("balance", 0)) / 100
    spent = float(result.get("amount_spent", 0)) / 100
    cap = result.get("spend_cap")
    remaining = None
    if cap:
        remaining = (float(cap) / 100) - spent
    return {"balance": balance, "spent": spent, "remaining": remaining}


def auto_optimize(account_id):
    """CPL-based optimization: if an ad set's CPL is 2x the best performer after
    MIN_DAYS_DATA days of data, pause it."""
    adsets = get_adset_insights(account_id, days=MIN_DAYS_DATA)
    if not adsets or len(adsets) < 2:
        return []

    actions_taken = []

    scored = []
    for a in adsets:
        spend = float(a.get("spend", 0))
        asid = a.get("adset_id")
        name = a.get("adset_name", "?")
        clicks = int(a.get("clicks", 0))

        link_clicks = 0
        leads = 0
        for action in a.get("actions", []):
            atype = action.get("action_type", "")
            val = int(action.get("value", 0))
            if atype == "link_click":
                link_clicks += val
            if atype in ("lead", "offsite_conversion.fb_pixel_lead"):
                leads += val

        conversions = leads if leads > 0 else link_clicks
        cpl = spend / conversions if conversions > 0 else float("inf")

        scored.append({
            "id": asid,
            "name": name,
            "spend": spend,
            "conversions": conversions,
            "cpl": cpl,
        })

    viable = [s for s in scored if s["spend"] >= MIN_SPEND_TO_JUDGE and s["conversions"] > 0]
    if len(viable) < 2:
        return []

    best_cpl = min(s["cpl"] for s in viable)
    if best_cpl <= 0 or best_cpl == float("inf"):
        return []

    for s in viable:
        if s["cpl"] >= best_cpl * CPL_PAUSE_MULTIPLIER:
            log(f"Auto-pausing: {s['name']} (CPL ${s['cpl']:.2f} is {s['cpl']/best_cpl:.1f}x the best ${best_cpl:.2f})")
            result = meta_api(f"/{s['id']}", method="POST", data={"status": "PAUSED"})
            if result.get("success"):
                actions_taken.append(
                    f"Paused '{s['name']}' — CPL ${s['cpl']:.2f} is {s['cpl']/best_cpl:.1f}x the best (${best_cpl:.2f})"
                )
            else:
                actions_taken.append(
                    f"Failed to pause '{s['name']}': {result.get('error', {}).get('message', '?')}"
                )

    if not actions_taken:
        best = min(viable, key=lambda x: x["cpl"])
        actions_taken.append(f"All ad sets within range. Best: '{best['name']}' at ${best['cpl']:.2f} CPL")

    return actions_taken


def store_daily_metrics(account_id):
    """Create or update the ad_metrics table with daily snapshots."""
    db = sqlite3.connect(BUS_DB)
    db.execute("""CREATE TABLE IF NOT EXISTS ad_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        account_id TEXT NOT NULL,
        impressions INTEGER DEFAULT 0,
        reach INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        ctr REAL DEFAULT 0,
        cpc REAL DEFAULT 0,
        cpm REAL DEFAULT 0,
        spend REAL DEFAULT 0,
        leads INTEGER DEFAULT 0,
        cpl REAL DEFAULT 0,
        link_clicks INTEGER DEFAULT 0,
        actions_json TEXT DEFAULT '{}',
        optimization_actions TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        UNIQUE(date, account_id)
    )""")
    db.commit()
    db.close()

    today_insights = get_account_insights(account_id, days=1)
    weekly_insights = get_account_insights(account_id, days=7)

    if not today_insights and not weekly_insights:
        log("No insights data available (campaigns may not have run yet)")
        return None

    ins = today_insights or weekly_insights
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    impressions = int(ins.get("impressions", 0))
    reach = int(ins.get("reach", 0))
    clicks = int(ins.get("clicks", 0))
    ctr = float(ins.get("ctr", 0))
    cpc = float(ins.get("cpc", 0))
    cpm = float(ins.get("cpm", 0))
    spend = float(ins.get("spend", 0))

    leads = 0
    link_clicks = 0
    for action in ins.get("actions", []):
        atype = action.get("action_type", "")
        val = int(action.get("value", 0))
        if atype in ("lead", "offsite_conversion.fb_pixel_lead"):
            leads += val
        if atype == "link_click":
            link_clicks += val

    cpl = spend / leads if leads > 0 else 0

    opt_actions = auto_optimize(account_id)

    db = sqlite3.connect(BUS_DB)
    db.execute("""INSERT OR REPLACE INTO ad_metrics
        (date, account_id, impressions, reach, clicks, ctr, cpc, cpm, spend, leads, cpl, link_clicks, actions_json, optimization_actions, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (today, account_id, impressions, reach, clicks, ctr, cpc, cpm, spend, leads, cpl, link_clicks,
         json.dumps(ins.get("actions", [])), json.dumps(opt_actions),
         datetime.now(timezone.utc).isoformat()))
    db.commit()
    db.close()

    return {
        "date": today,
        "impressions": impressions,
        "reach": reach,
        "clicks": clicks,
        "link_clicks": link_clicks,
        "ctr": round(ctr, 2),
        "cpc": round(cpc, 2),
        "cpm": round(cpm, 2),
        "spend": round(spend, 2),
        "leads": leads,
        "cpl": round(cpl, 2),
        "optimization_actions": opt_actions,
    }


def run_monitor():
    load_env()
    log("=" * 50)
    log("Ad Monitor starting daily check")

    accounts = get_ad_accounts()
    if not accounts:
        log("No ad accounts connected. System user needs ad account assignment.")
        bus_write("ad_monitor", "cora", "ad_performance", {
            "status": "no_accounts",
            "message": "No ad accounts connected. Sunheart needs to assign the system user to his Business Manager ad account.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, priority="high")
        return

    for account in accounts:
        acc_id = account["id"]
        acc_name = account.get("name", "Unnamed")
        acc_status = account.get("account_status", 0)
        log(f"Processing account: {acc_name} ({acc_id})")

        budget_info = check_budget(acc_id)
        metrics = store_daily_metrics(acc_id)
        campaigns = get_active_campaigns(acc_id)

        active_count = sum(1 for c in campaigns if c.get("status") == "ACTIVE")
        paused_count = sum(1 for c in campaigns if c.get("status") == "PAUSED")
        total_daily = sum(float(c.get("daily_budget", 0)) / 100 for c in campaigns if c.get("status") == "ACTIVE")

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account": acc_name,
            "account_id": acc_id,
            "account_status": {1: "Active", 2: "Disabled", 3: "Unsettled"}.get(acc_status, "Unknown"),
            "campaigns_active": active_count,
            "campaigns_paused": paused_count,
            "daily_spend_rate": round(total_daily, 2),
        }

        if budget_info:
            report["budget"] = budget_info
            remaining = budget_info.get("remaining")
            if remaining is not None:
                for threshold in sorted(BUDGET_ALERT_THRESHOLDS, reverse=True):
                    if remaining < threshold:
                        days_left = int(remaining / total_daily) if total_daily > 0 else "?"
                        severity = "CRITICAL" if threshold <= 20 else "WARNING"
                        alert_msg = (
                            f"{'🚨' if threshold <= 20 else '⚠️'} *{severity}: Low Ad Budget*\n"
                            f"Account: {acc_name}\n"
                            f"Remaining: ${remaining:.2f} (below ${threshold} threshold)\n"
                            f"At ${total_daily:.2f}/day, budget runs out in ~{days_left} days.\n"
                            f"Top up the Meta ad account NOW."
                        )
                        tg_notify(alert_msg)
                        report["budget_alert"] = threshold
                        log(f"BUDGET ALERT (${threshold}): ${remaining:.2f} remaining")
                        break

        if metrics:
            report["performance"] = metrics
            log(f"  Impressions: {metrics['impressions']}, Clicks: {metrics['clicks']}, CTR: {metrics['ctr']}%, Spend: ${metrics['spend']}")
            if metrics.get("optimization_actions"):
                log(f"  Optimization: {metrics['optimization_actions']}")

        bus_write("ad_monitor", "cora", "ad_performance", report, priority="medium", thread_id="ad_pipeline")

        summary_lines = [
            f"📊 *Daily Ad Report* — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            f"Account: {acc_name}",
            f"Active campaigns: {active_count}",
            f"Daily burn rate: ${total_daily:.2f}/day",
        ]
        if metrics:
            summary_lines.extend([
                f"Impressions: {metrics['impressions']}",
                f"Clicks: {metrics['clicks']} (CTR: {metrics['ctr']}%)",
                f"Link clicks: {metrics['link_clicks']}",
                f"Spend: ${metrics['spend']}",
                f"Leads: {metrics['leads']}",
            ])
            if metrics['cpl'] > 0:
                summary_lines.append(f"Cost per lead: ${metrics['cpl']}")
            if metrics.get("optimization_actions"):
                summary_lines.append(f"Auto-actions: {len(metrics['optimization_actions'])}")
                for a in metrics["optimization_actions"]:
                    summary_lines.append(f"  → {a}")
        else:
            summary_lines.append("No performance data yet (campaigns may be paused)")

        if budget_info:
            summary_lines.append(f"Budget remaining: ${budget_info.get('remaining', budget_info.get('balance', '?'))}")

        tg_notify("\n".join(summary_lines))
        log(f"Report written to bus and Telegram")

    log("Ad Monitor daily check complete")
    log("=" * 50)


if __name__ == "__main__":
    import urllib.parse
    run_monitor()
