"""triage — Phase 3 of the Sunheart Flow System.

Pulls CAPTURED items from Linear · classifies them with Claude · sets stream
priority + domain · routes to AI or Human lane · moves state to DISTILLED ·
adds a triage comment with rationale.

Run from cron (every 5 min):
    /opt/sh-brain-src/.venv/bin/python -m curator.triage

Idempotent · safe to re-run · skips items already triaged (detected via the
`triaged-by-ember:` marker in description or comments).

Streams (per James 2026-05-23):
    Stream 1 (⚡ Rapid Current)   · fastest moving · process every run
    Stream 2 (🌀 Active Flow)     · process every 6 runs (~30 min)
    Stream 3 (🍃 Slow River)       · process every 48 runs (~4 hr)
    Stream 4 (💤 Dormant Pool)     · catch-all · process daily
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Load /etc/sh-brain/curator.env directly (avoids shell-source parens issues
# when run from cron · systemd EnvironmentFile loads it fine for the service)
_ENV_FILE = Path(os.environ.get("CURATOR_ENV_FILE", "/etc/sh-brain/curator.env"))
if _ENV_FILE.is_file():
    try:
        for line in _ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k and k not in os.environ:
                os.environ[k] = v.strip()
    except Exception:
        pass

log = logging.getLogger("curator.triage")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# ─── Linear config ────────────────────────────────────────────────────────
LINEAR_TOKEN_PATH = os.environ.get(
    "LINEAR_API_TOKEN_PATH",
    str(Path.home() / ".config" / "fpai" / "linear" / "api.token"),
)
LINEAR_TEAM_ID = os.environ.get(
    "LINEAR_TEAM_ID", "44963b86-9bc7-4cc1-8440-d094711408f8"
)
LINEAR_API = "https://api.linear.app/graphql"

# State name → ID will be looked up at runtime
STATE_NAMES = {
    "CAPTURED": "1. CAPTURED",
    "DISTILLED": "2. DISTILLED",
    "AI_EXECUTING": "3. AI EXECUTING",
    "HUMAN_ASSIST": "4. HUMAN ASSIST",
}

LABEL_NAMES = {
    "stream_1": "⚡ Rapid Current",
    "stream_2": "🌀 Active Flow",
    "stream_3": "🍃 Slow River",
    "stream_4": "💤 Dormant Pool",
}

# ─── Anthropic config ─────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or ""
ANTHROPIC_MODEL = os.environ.get(
    "CURATOR_ANTHROPIC_MODEL", "claude-sonnet-4-20250514"
)
ANTHROPIC_API = "https://api.anthropic.com/v1/messages"

TRIAGE_MARKER = "triaged-by-ember"
ROUTING_MARKER = "routed-by-ember"

# Per-run safety caps
MAX_TRIAGE_PER_RUN = int(os.environ.get("TRIAGE_MAX_PER_RUN", "5"))
MAX_ROUTE_PER_RUN = int(os.environ.get("ROUTE_MAX_PER_RUN", "5"))


# ─── helpers ──────────────────────────────────────────────────────────────

def linear_token() -> str:
    return Path(LINEAR_TOKEN_PATH).expanduser().read_text().strip()


def linear_post(query: str, variables: dict | None = None) -> dict:
    token = linear_token()
    with httpx.Client(timeout=20.0) as cli:
        r = cli.post(
            LINEAR_API,
            headers={"Authorization": token, "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
        )
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(f"Linear errors: {data['errors']}")
        return data["data"]


def get_states() -> dict[str, str]:
    """Returns {state_name: state_id}."""
    q = """
    query($teamId: ID!) {
      workflowStates(filter: {team: {id: {eq: $teamId}}}) {
        nodes { id name }
      }
    }
    """
    d = linear_post(q, {"teamId": LINEAR_TEAM_ID})
    return {n["name"]: n["id"] for n in d["workflowStates"]["nodes"]}


def get_labels() -> dict[str, str]:
    """Returns {label_name: label_id}."""
    q = """
    query($teamId: ID!) {
      issueLabels(filter: {team: {id: {eq: $teamId}}}) {
        nodes { id name }
      }
    }
    """
    d = linear_post(q, {"teamId": LINEAR_TEAM_ID})
    return {n["name"]: n["id"] for n in d["issueLabels"]["nodes"]}


def get_captured_issues(state_id: str, limit: int = 20) -> list[dict]:
    """Pull CAPTURED items · most recent first · skip already-triaged."""
    q = """
    query($teamId: ID!, $stateId: ID!, $first: Int!) {
      issues(
        filter: {team: {id: {eq: $teamId}}, state: {id: {eq: $stateId}}},
        first: $first,
        orderBy: createdAt
      ) {
        nodes {
          id identifier title description createdAt
          state { id name }
          labels { nodes { id name } }
          comments { nodes { body } }
        }
      }
    }
    """
    d = linear_post(q, {"teamId": LINEAR_TEAM_ID, "stateId": state_id, "first": limit})
    out: list[dict] = []
    for n in d["issues"]["nodes"]:
        # Skip if already-triaged marker exists
        desc = n.get("description") or ""
        comments_body = " ".join(c["body"] for c in (n.get("comments", {}).get("nodes") or []))
        if TRIAGE_MARKER in desc or TRIAGE_MARKER in comments_body:
            continue
        out.append(n)
    return out


def update_issue(issue_id: str, state_id: str, label_ids: list[str]) -> None:
    q = """
    mutation($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) { success }
    }
    """
    linear_post(q, {
        "id": issue_id,
        "input": {"stateId": state_id, "labelIds": label_ids},
    })


def add_comment(issue_id: str, body: str) -> None:
    q = """
    mutation($input: CommentCreateInput!) {
      commentCreate(input: $input) { success }
    }
    """
    linear_post(q, {"input": {"issueId": issue_id, "body": body}})


# ─── Claude triage ────────────────────────────────────────────────────────

TRIAGE_PROMPT = """You are the Sunheart Flow Triage agent. Classify this CAPTURED intent for James (vision-led founder · Costa Rica · building CORA Nation umbrella ecosystem · 4 pillars: OneBPO · Zen Village · Full Potential · Coherence Course).

Return ONLY a JSON object with these fields:
{
  "stream": 1|2|3|4,
  "domain": "treasury|village|game|vision|ops|personal|build|legal|other",
  "route": "AI-only|Human-needed|Both",
  "next_action": "<one-sentence concrete next step>",
  "reasoning": "<one-sentence why this classification>"
}

Stream guide:
- 1 (Rapid Current) = blocker · cash-impacting · urgent decision · time-critical · drop-everything
- 2 (Active Flow) = important · in-motion · this-week work · clear ownership
- 3 (Slow River) = later · steady · no rush · backlog candidate
- 4 (Dormant Pool) = parked · vague · low-priority · idea-only

Route guide:
- AI-only = Ember/Forge/Kai can execute end-to-end · no James input needed
- Human-needed = irreducibly James (vision · signatures · personal presence · WhatsApp QR · MetaMask)
- Both = AI drafts/builds · James ratifies or completes one tap

ITEM TO CLASSIFY:
Title: __TITLE__
Description: __DESCRIPTION__
Current labels: __LABELS__

Return ONLY the JSON · no preamble."""


def claude_classify(title: str, description: str, labels: list[str]) -> dict | None:
    if not ANTHROPIC_API_KEY:
        log.warning("triage: ANTHROPIC_API_KEY missing · skipping")
        return None
    prompt = (
        TRIAGE_PROMPT
        .replace("__TITLE__", title or "(no title)")
        .replace("__DESCRIPTION__", (description or "")[:2000])
        .replace("__LABELS__", ", ".join(labels) or "(none)")
    )
    try:
        with httpx.Client(timeout=30.0) as cli:
            r = cli.post(
                ANTHROPIC_API,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            txt = r.json()["content"][0]["text"].strip()
            # Strip markdown fences if present
            txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.MULTILINE).strip()
            return json.loads(txt)
    except Exception as e:
        log.warning("triage: Claude classify failed: %s", e)
        return None


# ─── Main triage loop ─────────────────────────────────────────────────────

def triage_one(issue: dict, states: dict, labels: dict) -> bool:
    """Triage a single issue. Returns True if processed."""
    title = issue["title"]
    desc = issue.get("description") or ""
    current_labels = [l["name"] for l in issue["labels"]["nodes"]]

    classification = claude_classify(title, desc, current_labels)
    if not classification:
        log.warning("triage: %s · classification failed · skipping", issue["identifier"])
        return False

    stream = int(classification.get("stream", 1))
    domain = classification.get("domain", "other")
    route = classification.get("route", "Both")
    next_action = classification.get("next_action", "")
    reasoning = classification.get("reasoning", "")

    # Build new label list: keep existing non-stream labels + correct stream label
    stream_label_id = labels.get(LABEL_NAMES[f"stream_{stream}"])
    new_label_ids = [
        l["id"] for l in issue["labels"]["nodes"]
        if l["name"] not in LABEL_NAMES.values()
    ]
    if stream_label_id:
        new_label_ids.append(stream_label_id)

    # Move state: → DISTILLED always · later phases will push further
    distilled_id = states.get(STATE_NAMES["DISTILLED"])
    if not distilled_id:
        log.warning("triage: DISTILLED state not found · skipping")
        return False

    update_issue(issue["id"], distilled_id, new_label_ids)

    # Add classification comment with TRIAGE_MARKER so we don't re-triage
    comment = (
        f"**{TRIAGE_MARKER}** · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"- **Stream**: {stream} ({LABEL_NAMES[f'stream_{stream}']})\n"
        f"- **Domain**: {domain}\n"
        f"- **Route**: {route}\n"
        f"- **Next action**: {next_action}\n"
        f"- **Why**: {reasoning}\n\n"
        f"_Moved CAPTURED → DISTILLED · classified by Ember · v1 triage._"
    )
    add_comment(issue["id"], comment)
    log.info(
        "triage: %s · stream=%s · domain=%s · route=%s",
        issue["identifier"], stream, domain, route,
    )
    return True


# ─── Phase 3.5 · post-triage routing ──────────────────────────────────────

# Parse the route from the triage comment we already left
_ROUTE_RE = re.compile(r"\*\*Route\*\*:\s*(AI-only|Human-needed|Both)", re.IGNORECASE)
_NEXT_ACTION_RE = re.compile(r"\*\*Next action\*\*:\s*(.+?)(?:\n|$)")
_STREAM_RE = re.compile(r"\*\*Stream\*\*:\s*(\d)")
_DOMAIN_RE = re.compile(r"\*\*Domain\*\*:\s*(\w+)")


def get_distilled_unrouted(state_id: str, limit: int = 20) -> list[dict]:
    """DISTILLED items that have triage comment but not yet routing comment."""
    q = """
    query($teamId: ID!, $stateId: ID!, $first: Int!) {
      issues(
        filter: {team: {id: {eq: $teamId}}, state: {id: {eq: $stateId}}},
        first: $first,
        orderBy: updatedAt
      ) {
        nodes {
          id identifier title description url
          comments { nodes { body } }
        }
      }
    }
    """
    d = linear_post(q, {"teamId": LINEAR_TEAM_ID, "stateId": state_id, "first": limit})
    out: list[dict] = []
    for n in d["issues"]["nodes"]:
        all_text = " ".join(c["body"] for c in (n.get("comments", {}).get("nodes") or []))
        if TRIAGE_MARKER not in all_text:
            continue  # not triaged yet · skip
        if ROUTING_MARKER in all_text:
            continue  # already routed
        out.append(n)
    return out


def _extract_route_info(comments: list[dict]) -> dict:
    """Pull route + next_action + stream + domain from the triage comment."""
    for c in comments:
        body = c.get("body") or ""
        if TRIAGE_MARKER not in body:
            continue
        info: dict = {}
        if m := _ROUTE_RE.search(body):
            info["route"] = m.group(1)
        if m := _NEXT_ACTION_RE.search(body):
            info["next_action"] = m.group(1).strip()
        if m := _STREAM_RE.search(body):
            info["stream"] = int(m.group(1))
        if m := _DOMAIN_RE.search(body):
            info["domain"] = m.group(1)
        return info
    return {}


def update_issue_state(issue_id: str, state_id: str) -> None:
    """State-only update (preserves labels). Separate from full update_issue."""
    q = """
    mutation($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) { success }
    }
    """
    linear_post(q, {"id": issue_id, "input": {"stateId": state_id}})


def _file_human_ask(issue: dict, route_info: dict) -> str | None:
    """File a james_ask for a Human-needed item. Returns ask_id or None."""
    try:
        from . import james_ask  # late import · keeps triage.py runnable standalone if module missing
    except Exception as e:
        log.warning("route: james_ask import failed: %s", e)
        return None

    stream = route_info.get("stream", 1)
    priority_map = {1: "rapid", 2: "active", 3: "slow", 4: "dormant"}
    next_action = route_info.get("next_action") or "Decide what to do with this item."

    question = f"{next_action}"
    if not question.endswith("?"):
        question += " · proceed?"

    context = (
        f"From Linear {issue['identifier']} ({issue.get('title', '')[:80]})\n"
        f"Domain: {route_info.get('domain', 'other')} · Stream: {stream}\n"
        f"View: {issue.get('url', '')}\n"
        f"Reply Y to proceed · N to skip · or describe what to do instead."
    )

    try:
        ask_id = james_ask.create_ask(
            question=question,
            context=context,
            from_agent="triage-router",
            priority=priority_map.get(stream, "rapid"),
            options=["Y · proceed", "N · skip / dormant", "Explain X"],
            metadata={"linear_issue_id": issue["id"], "linear_identifier": issue["identifier"]},
        )
        return ask_id
    except Exception as e:
        log.warning("route: create_ask failed for %s: %s", issue["identifier"], e)
        return None


def route_one(issue: dict, states: dict) -> bool:
    """Route a DISTILLED item. Returns True if processed."""
    route_info = _extract_route_info(issue["comments"]["nodes"])
    route = route_info.get("route")
    if not route:
        log.warning("route: %s · no route in triage comment · skipping", issue["identifier"])
        return False

    ai_executing_id = states.get(STATE_NAMES["AI_EXECUTING"])
    actions: list[str] = []
    ask_id: str | None = None

    if route in ("AI-only", "Both"):
        if ai_executing_id:
            update_issue_state(issue["id"], ai_executing_id)
            actions.append("moved → AI EXECUTING (queued)")
        else:
            actions.append("⚠️ AI EXECUTING state not found · staying in DISTILLED")

    if route in ("Human-needed", "Both"):
        ask_id = _file_human_ask(issue, route_info)
        if ask_id:
            actions.append(f"filed james_ask: `{ask_id}`")
        else:
            actions.append("⚠️ james_ask file failed")

    comment = (
        f"**{ROUTING_MARKER}** · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Route: **{route}**\n"
        f"Actions:\n"
        + "\n".join(f"- {a}" for a in actions)
        + "\n\n_v1 routing · auto-executor coming Phase 3.6._"
    )
    add_comment(issue["id"], comment)
    log.info("route: %s · route=%s · actions=%s", issue["identifier"], route, actions)
    return True


def run_once() -> dict:
    """Run a single triage + routing pass. Returns stats."""
    states = get_states()
    labels = get_labels()
    captured_id = states.get(STATE_NAMES["CAPTURED"])
    distilled_id = states.get(STATE_NAMES["DISTILLED"])
    if not captured_id or not distilled_id:
        log.error("triage: CAPTURED or DISTILLED state not found")
        return {"error": "missing_states"}

    # Phase 3: CAPTURED → DISTILLED
    captured = get_captured_issues(captured_id, limit=MAX_TRIAGE_PER_RUN * 4)
    triaged = 0
    for issue in captured[:MAX_TRIAGE_PER_RUN]:
        try:
            if triage_one(issue, states, labels):
                triaged += 1
        except Exception as e:
            log.exception("triage: %s · error: %s", issue["identifier"], e)

    # Phase 3.5: DISTILLED → AI EXECUTING / file ask
    distilled = get_distilled_unrouted(distilled_id, limit=MAX_ROUTE_PER_RUN * 4)
    routed = 0
    for issue in distilled[:MAX_ROUTE_PER_RUN]:
        try:
            if route_one(issue, states):
                routed += 1
        except Exception as e:
            log.exception("route: %s · error: %s", issue["identifier"], e)

    return {
        "triaged": triaged,
        "triage_pending": max(0, len(captured) - triaged),
        "routed": routed,
        "route_pending": max(0, len(distilled) - routed),
    }


if __name__ == "__main__":
    stats = run_once()
    print(json.dumps(stats))
