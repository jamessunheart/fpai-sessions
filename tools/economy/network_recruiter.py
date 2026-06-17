#!/usr/bin/env python3
"""Role-gap detection and dry-run network recruiting signals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

NETWORK_ROLES = ("seeker", "coach", "builder", "validator", "connector", "patron", "anchor")
ROLE_TARGETS = {
    "seeker": 20,
    "coach": 5,
    "builder": 10,
    "validator": 5,
    "connector": 3,
    "patron": 1,
    "anchor": 1,
}
ROLE_KEYWORDS = {
    "seeker": ("stuck", "full potential", "purpose", "growth", "clarity"),
    "coach": ("coach", "mentor", "helped", "guided", "facilitator"),
    "builder": ("github", "built", "code", "design", "curriculum", "integration", "tool"),
    "validator": ("review", "audit", "quality", "proof", "verify", "evaluator"),
    "connector": ("community", "network", "introductions", "audience", "newsletter", "podcast"),
    "patron": ("fund", "grant", "invest", "philanthropy", "capital", "donor"),
    "anchor": ("founder", "public", "mission", "speaker", "story", "embodies"),
}
ROLE_OUTREACH = {
    "seeker": "Sunheart AI helps you reach your full potential and grows to serve your specific path.",
    "builder": "Sunheart is building infrastructure for human potential - your skills are directly relevant.",
    "connector": "The network is growing - your reach could shape who enters it.",
    "validator": "Sunheart is building trustable human-potential infrastructure - your review signal could raise the quality bar.",
    "patron": "Sunheart is turning capital into durable human-potential infrastructure instead of extractive platform fees.",
    "anchor": "Sunheart needs public embodiments of the mission - your story could help people recognize the path.",
    "coach": "Sunheart routes stuck seekers to people who have navigated the terrain - your lived knowledge could help directly.",
}


@dataclass(frozen=True)
class RoleGap:
    role: str
    current_count: int
    target_count: int
    missing: int
    search_signal: str

    def row(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "current_count": self.current_count,
            "target_count": self.target_count,
            "missing": self.missing,
            "search_signal": self.search_signal,
        }


def role_counts(members: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {role: 0 for role in NETWORK_ROLES}
    for member in members:
        role = _role(member.get("role_signal") or member.get("role") or member.get("network_role"))
        if role in counts:
            counts[role] += 1
    return counts


def identify_role_gaps(
    *,
    members: Iterable[dict[str, Any]] = (),
    targets: dict[str, int] | None = None,
) -> list[RoleGap]:
    wanted = targets or ROLE_TARGETS
    counts = role_counts(members)
    gaps: list[RoleGap] = []
    for role in NETWORK_ROLES:
        target = int(wanted.get(role, 0))
        current = counts.get(role, 0)
        missing = max(0, target - current)
        if missing:
            gaps.append(
                RoleGap(
                    role=role,
                    current_count=current,
                    target_count=target,
                    missing=missing,
                    search_signal=_search_signal(role),
                )
            )
    return sorted(gaps, key=lambda gap: (gap.missing / max(gap.target_count, 1), gap.missing), reverse=True)


def infer_role_signal(text: str, *, platform: str | None = None) -> str:
    haystack = " ".join(str(text or "").lower().split())
    scores: dict[str, int] = {}
    for role, keywords in ROLE_KEYWORDS.items():
        scores[role] = sum(1 for keyword in keywords if keyword in haystack)
    if (platform or "").lower() in {"github", "hackernews", "hn"}:
        scores["builder"] += 1
    best_role, best_score = max(scores.items(), key=lambda item: (item[1], NETWORK_ROLES.index(item[0]) * -1))
    return best_role if best_score > 0 else "seeker"


def generate_role_signal(contact: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(contact.get(key) or "")
        for key in ("bio", "description", "topic_signal", "source_text", "metadata")
    )
    platform = str(contact.get("platform") or "")
    role = _role(contact.get("role_signal")) or infer_role_signal(text, platform=platform)
    return {
        "handle": contact.get("handle") or contact.get("identifier"),
        "platform": platform,
        "role_signal": role,
        "outreach_angle": ROLE_OUTREACH[role],
        "discovery_weight": discovery_weight(role),
    }


def discovery_weight(role: str) -> float:
    role = _role(role) or "seeker"
    if role in {"patron", "validator", "builder"}:
        return 1.0
    if role in {"connector", "anchor"}:
        return 0.85
    return 0.65


def beacon_search_signals(gaps: Iterable[RoleGap | dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for gap in gaps:
        row = gap.row() if isinstance(gap, RoleGap) else dict(gap)
        rows.append(
            {
                "role_signal": row["role"],
                "topic_signal": row["search_signal"],
                "weight": discovery_weight(row["role"]),
                "reason": f"{row['role']} count {row['current_count']} below target {row['target_count']}",
            }
        )
    return rows


def _search_signal(role: str) -> str:
    if role == "validator":
        return "quality reviewer validator proof outcomes human potential"
    if role == "patron":
        return "philanthropy funder grant human potential conscious technology"
    if role == "builder":
        return "GitHub Hacker News builder AI tools human potential"
    if role == "connector":
        return "community builder newsletter podcast human potential network"
    if role == "anchor":
        return "public founder speaker mission human potential story"
    if role == "coach":
        return "coach mentor burnout career relationships purpose"
    return "full potential seeker stuck purpose growth clarity"


def _role(value: Any) -> str:
    cleaned = " ".join(str(value or "").strip().lower().split())
    return cleaned if cleaned in NETWORK_ROLES else ""
