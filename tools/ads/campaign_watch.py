#!/usr/bin/env python3
"""Meta campaign watch and guarded campaign actions.

The access token is read only from the live service environment. Reports are
written to files that Codex sessions can consume without credential exposure.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


DEFAULT_CAMPAIGN_ID = "52555196349772"
DEFAULT_ACCOUNT_ID = "act_71883338"
DEFAULT_API_VERSION = "v19.0"
DEFAULT_STATUS = Path.home() / ".config/fpai/ads/status.json"
DEFAULT_HOT_STATE = Path.home() / ".config/fpai/hot_memory/ads_status.json"
DEFAULT_ALLOCATION_LEDGER = Path.home() / ".config/fpai/allocation/ledger.jsonl"
DEFAULT_ACTION_PORT = 8765
DEFAULT_AI_TOKEN_FILE = Path.home() / ".config/fpai/ai.token"
MAX_DAILY_BUDGET_USD = 20.0
DAILY_SPEND_ALERT_USD = 12.0
CPL_ALERT_USD = 15.0

LEAD_ACTION_TYPES = {
    "lead",
    "onsite_conversion.lead_grouped",
    "offsite_conversion.fb_pixel_lead",
    "offsite_conversion.custom",
}


class CampaignWatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class MetaConfig:
    access_token: str
    campaign_id: str = DEFAULT_CAMPAIGN_ID
    account_id: str = DEFAULT_ACCOUNT_ID
    api_version: str = DEFAULT_API_VERSION
    base_url: str = "https://graph.facebook.com"

    @classmethod
    def from_env(cls) -> "MetaConfig":
        token = os.environ.get("META_ACCESS_TOKEN", "").strip()
        if not token:
            raise CampaignWatchError("META_ACCESS_TOKEN missing from service environment")
        return cls(
            access_token=token,
            campaign_id=os.environ.get("META_CAMPAIGN_ID", DEFAULT_CAMPAIGN_ID),
            account_id=os.environ.get("META_AD_ACCOUNT_ID", DEFAULT_ACCOUNT_ID),
            api_version=os.environ.get("META_API_VERSION", DEFAULT_API_VERSION),
        )


class MetaClient:
    def __init__(
        self,
        config: MetaConfig,
        *,
        opener: Callable[[urllib.request.Request, int], Any] | None = None,
    ) -> None:
        self.config = config
        self._opener = opener or urllib.request.urlopen

    def request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = dict(params or {})
        params["access_token"] = self.config.access_token
        encoded = urllib.parse.urlencode(params, doseq=True)
        url = f"{self.config.base_url}/{self.config.api_version}/{path.lstrip('/')}"
        data = None
        if method.upper() == "GET":
            url = f"{url}?{encoded}"
        else:
            data = encoded.encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method.upper())
        try:
            with self._opener(req, 30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"error": {"message": body or str(exc)}}
            err = parsed.get("error") or {}
            message = err.get("message") or str(exc)
            code = err.get("code")
            raise CampaignWatchError(f"Meta API error {code}: {message}") from exc

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("GET", path, params)

    def post(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("POST", path, params)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def today_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def first_row(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, list) and data:
        return data[0] if isinstance(data[0], dict) else {}
    return {}


def lead_count(insight: dict[str, Any]) -> int:
    total = 0
    for action in insight.get("actions") or []:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("action_type", ""))
        if action_type in LEAD_ACTION_TYPES or action_type.endswith(".lead"):
            total += safe_int(action.get("value"))
    return total


def money(value: float) -> float:
    return round(float(value), 2)


def normalize_insight(row: dict[str, Any]) -> dict[str, Any]:
    spend = safe_float(row.get("spend"))
    leads = lead_count(row)
    return {
        "spend": money(spend),
        "impressions": safe_int(row.get("impressions")),
        "clicks": safe_int(row.get("clicks")),
        "leads": leads,
        "cpl": money(spend / leads) if leads else None,
        "actions": row.get("actions") or [],
    }


def review_state(campaign: dict[str, Any], adsets: list[dict[str, Any]], ads: list[dict[str, Any]]) -> str:
    entities = [campaign, *adsets, *ads]
    feedback = [e.get("ad_review_feedback") or e.get("review_feedback") for e in entities]
    if any(bool(item) for item in feedback):
        return "review_feedback"
    statuses = {str(e.get("effective_status", "")).upper() for e in entities if e.get("effective_status")}
    if "PENDING_REVIEW" in statuses or "IN_PROCESS" in statuses:
        return "pending_review"
    if statuses and statuses <= {"ACTIVE", "PAUSED", "CAMPAIGN_PAUSED", "ADSET_PAUSED"}:
        return "approved"
    return "unknown"


def account_has_error(account: dict[str, Any]) -> bool:
    status = safe_int(account.get("account_status"))
    disable_reason = safe_int(account.get("disable_reason"))
    return bool((status and status != 1) or disable_reason)


def get_insight(client: MetaClient, campaign_id: str, *, today_only: bool) -> dict[str, Any]:
    params: dict[str, Any] = {"fields": "spend,impressions,clicks,actions", "level": "campaign"}
    if today_only:
        today = today_utc()
        params["time_range"] = json.dumps({"since": today, "until": today})
    else:
        params["date_preset"] = "maximum"
    return normalize_insight(first_row(client.get(f"{campaign_id}/insights", params)))


def collect_status(client: MetaClient) -> dict[str, Any]:
    cfg = client.config
    campaign = client.get(
        cfg.campaign_id,
        {"fields": "id,name,status,configured_status,effective_status,ad_review_feedback,review_feedback"},
    )
    adsets = client.get(
        f"{cfg.campaign_id}/adsets",
        {"fields": "id,name,status,configured_status,effective_status,daily_budget,ad_review_feedback"},
    ).get("data") or []
    ads = client.get(
        f"{cfg.campaign_id}/ads",
        {"fields": "id,name,status,configured_status,effective_status,ad_review_feedback"},
    ).get("data") or []
    account = client.get(
        cfg.account_id,
        {"fields": "id,account_status,disable_reason,amount_spent,balance,currency,funding_source_details"},
    )
    today = get_insight(client, cfg.campaign_id, today_only=True)
    total = get_insight(client, cfg.campaign_id, today_only=False)
    return {
        "schema": "fpai.ads.status.v1",
        "generated_at": now_utc(),
        "campaign_id": cfg.campaign_id,
        "account_id": cfg.account_id,
        "campaign": campaign,
        "review_status": review_state(campaign, adsets, ads),
        "adsets": adsets,
        "ads": ads,
        "spend_today": today["spend"],
        "spend_total": total["spend"],
        "impressions_today": today["impressions"],
        "impressions_total": total["impressions"],
        "clicks_today": today["clicks"],
        "clicks_total": total["clicks"],
        "leads_today": today["leads"],
        "leads_total": total["leads"],
        "cpl_today": today["cpl"],
        "cpl_total": total["cpl"],
        "billing": {
            "account_status": account.get("account_status"),
            "disable_reason": account.get("disable_reason"),
            "amount_spent": account.get("amount_spent"),
            "balance": account.get("balance"),
            "currency": account.get("currency"),
            "funding_source_details": account.get("funding_source_details"),
            "has_error": account_has_error(account),
        },
    }


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def alert_reasons(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if previous:
        if previous.get("review_status") != "approved" and current.get("review_status") == "approved":
            reasons.append("review approved")
        if safe_float(previous.get("spend_total")) <= 0 < safe_float(current.get("spend_total")):
            reasons.append("first spend")
    if current.get("cpl_today") is not None and safe_float(current.get("cpl_today")) > CPL_ALERT_USD:
        reasons.append(f"CPL > ${CPL_ALERT_USD:g}")
    if safe_float(current.get("spend_today")) > DAILY_SPEND_ALERT_USD:
        reasons.append(f"daily spend > ${DAILY_SPEND_ALERT_USD:g}")
    if current.get("billing", {}).get("has_error"):
        reasons.append("account/billing error")
    return reasons


def default_notifier(message: str, *, repo_root: Path) -> bool:
    script = repo_root / "tools/build_loop/notify_telegram.sh"
    if not script.exists():
        return False
    result = subprocess.run([str(script), message], capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def notify_if_needed(
    reasons: list[str],
    status: dict[str, Any],
    *,
    repo_root: Path,
    notifier: Callable[[str], bool] | None = None,
) -> bool:
    if not reasons:
        return False
    message = (
        "Campaign Watch: "
        + ", ".join(reasons)
        + f" | spend_today=${safe_float(status.get('spend_today')):.2f}"
        + f" | cpl_today={status.get('cpl_today')}"
        + f" | campaign={status.get('campaign_id')}"
    )
    send = notifier or (lambda text: default_notifier(text, repo_root=repo_root))
    return bool(send(message))


def allocation_row(status: dict[str, Any], reasons: list[str], notified: bool) -> dict[str, Any]:
    return {
        "ts": status["generated_at"],
        "kind": "level3_stewardship_allocation",
        "source": "campaign_watch",
        "campaign_id": status["campaign_id"],
        "account_id": status["account_id"],
        "spend_today_usd": status["spend_today"],
        "spend_total_usd": status["spend_total"],
        "impressions_today": status["impressions_today"],
        "clicks_today": status["clicks_today"],
        "leads_today": status["leads_today"],
        "cpl_today_usd": status["cpl_today"],
        "review_status": status["review_status"],
        "billing_error": status["billing"]["has_error"],
        "alerts": reasons,
        "telegram_notified": notified,
    }


def run_watch(
    *,
    client: MetaClient,
    status_path: Path,
    hot_state_path: Path,
    allocation_ledger: Path,
    repo_root: Path,
    notify: bool,
    notifier: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    previous = read_json(status_path)
    status = collect_status(client)
    reasons = alert_reasons(previous, status)
    notified = notify_if_needed(reasons, status, repo_root=repo_root, notifier=notifier) if notify else False
    write_json(status_path, status)
    write_json(hot_state_path, status)
    append_jsonl(allocation_ledger, allocation_row(status, reasons, notified))
    return status


def list_adsets(client: MetaClient) -> list[dict[str, Any]]:
    return client.get(f"{client.config.campaign_id}/adsets", {"fields": "id,name,daily_budget"}).get("data") or []


def perform_action(client: MetaClient, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    campaign_id = client.config.campaign_id
    if action == "pause_campaign":
        result = client.post(campaign_id, {"status": "PAUSED"})
        return {"ok": True, "action": action, "result": result}
    if action == "resume_campaign":
        result = client.post(campaign_id, {"status": "ACTIVE"})
        return {"ok": True, "action": action, "result": result}
    if action == "set_daily_budget":
        budget = safe_float(payload.get("daily_budget_usd"))
        if budget <= 0:
            raise CampaignWatchError("daily_budget_usd must be positive")
        if budget > MAX_DAILY_BUDGET_USD:
            raise CampaignWatchError(f"daily budget hard ceiling is ${MAX_DAILY_BUDGET_USD:g}/day")
        cents = int(round(budget * 100))
        results = []
        for adset in list_adsets(client):
            adset_id = adset.get("id")
            if adset_id:
                results.append({"adset_id": adset_id, "result": client.post(adset_id, {"daily_budget": str(cents)})})
        return {"ok": True, "action": action, "daily_budget_usd": money(budget), "updated_adsets": results}
    raise CampaignWatchError(f"unsupported action: {action}")


def bearer_authorized(header: str | None, expected: str) -> bool:
    if not expected:
        return False
    prefix = "Bearer "
    return bool(header and header.startswith(prefix) and header[len(prefix) :] == expected)


def load_action_token() -> str:
    token = os.environ.get("FPAI_ADS_ACTION_TOKEN") or os.environ.get("FPAI_AI_TOKEN") or ""
    if token.strip():
        return token.strip()
    token_file = (
        os.environ.get("FPAI_ADS_ACTION_TOKEN_FILE")
        or os.environ.get("FPAI_AI_TOKEN_FILE")
        or str(DEFAULT_AI_TOKEN_FILE)
    )
    try:
        return Path(token_file).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def make_handler(client_factory: Callable[[], MetaClient], bearer_token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "FPAICampaignActions/1.0"

        def _send(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._send(200, {"ok": True, "service": "campaign_actions"})
                return
            self._send(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/actions":
                self._send(404, {"ok": False, "error": "not found"})
                return
            if not bearer_authorized(self.headers.get("Authorization"), bearer_token):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw.decode("utf-8") or "{}")
                result = perform_action(client_factory(), str(body.get("action", "")), body)
                self._send(200, result)
            except (json.JSONDecodeError, CampaignWatchError) as exc:
                self._send(400, {"ok": False, "error": str(exc)})
            except Exception as exc:  # Token and request details must not leak.
                self._send(500, {"ok": False, "error": exc.__class__.__name__})

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("campaign_actions: " + fmt % args + "\n")

    return Handler


def serve_actions(host: str, port: int, client_factory: Callable[[], MetaClient], bearer_token: str) -> None:
    if not bearer_token:
        raise CampaignWatchError("AI action bearer token missing; refusing to start action endpoint")
    server = ThreadingHTTPServer((host, port), make_handler(client_factory, bearer_token))
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Collect status once and write reports.")
    parser.add_argument("--serve-actions", action="store_true", help="Run the guarded actions endpoint.")
    parser.add_argument("--host", default=os.environ.get("FPAI_ADS_ACTION_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("FPAI_ADS_ACTION_PORT", DEFAULT_ACTION_PORT)))
    parser.add_argument("--status-path", type=Path, default=Path(os.environ.get("FPAI_ADS_STATUS_PATH", DEFAULT_STATUS)))
    parser.add_argument("--hot-state-path", type=Path, default=Path(os.environ.get("FPAI_ADS_HOT_STATE_PATH", DEFAULT_HOT_STATE)))
    parser.add_argument(
        "--allocation-ledger",
        type=Path,
        default=Path(os.environ.get("FPAI_ALLOCATION_LEDGER", DEFAULT_ALLOCATION_LEDGER)),
    )
    parser.add_argument("--repo-root", type=Path, default=Path(os.environ.get("FPAI_REPO", Path(__file__).resolve().parents[2])))
    parser.add_argument("--no-notify", action="store_true", help="Skip Telegram state-change alerts.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.once and not args.serve_actions:
        args.once = True

    def client_factory() -> MetaClient:
        return MetaClient(MetaConfig.from_env())

    if args.serve_actions:
        serve_actions(args.host, args.port, client_factory, load_action_token())
        return 0
    status = run_watch(
        client=client_factory(),
        status_path=args.status_path,
        hot_state_path=args.hot_state_path,
        allocation_ledger=args.allocation_ledger,
        repo_root=args.repo_root,
        notify=not args.no_notify,
    )
    print(json.dumps({"ok": True, "status_path": str(args.status_path), "generated_at": status["generated_at"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
