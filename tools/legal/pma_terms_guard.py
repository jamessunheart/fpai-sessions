from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TERMS_PATH = REPO_ROOT / "docs/legal/pma/PMA_MEMBERSHIP_TERMS_PATRON_ENGINE.md"
COUNCIL_REVIEW_PATH = REPO_ROOT / "core/BUILD/reviews/SPEC_d087_pma-membership-terms-council-rev.council.md"


REQUIRED_TERMS = (
    "Status:** Draft",
    "not legal advice",
    "Membership Access Door",
    "Patron Gift Door",
    "Standing Utility Rule",
    "Member Rights",
    "Patronage Flow",
    "No Equity, No Return, No Securities",
    "does not grant ownership, equity",
    "No member should expect profit",
    "Patronage records are membership records only",
    "not live until",
    "qualified counsel reviews",
)

REQUIRED_COUNCIL_REVIEW = (
    "Pragmatist",
    "Legal Skeptic",
    "Member Advocate",
    "Stewardship Lens",
    "Council verdict",
    "Not approved for signature",
)

PROHIBITED_POSITIVE_PATTERNS = (
    r"\bguaranteed\s+(?:profit|profits|return|returns|yield|income|upside)\b",
    r"\b(?:is|as|provides|offers|creates)\s+(?:a\s+)?passive\s+income\b",
    r"\breturn\s+on\s+investment\s+is\b",
    r"\bmembers?\s+(?:will|shall)\s+receive\s+(?:profits?|returns?|yield|dividends?)\b",
    r"\bprofit[-\s]?sharing\b",
    r"\bequity\s+stake\b",
    r"\b(?:receive|receives|grant|grants|own|owns)\s+(?:an?\s+)?ownership\s+stake\b",
    r"\bdividends?\s+(?:will|shall)\s+be\s+paid\b",
    r"\bappreciat(?:e|ion)\s+in\s+value\s+for\s+members\b",
    r"\btax[-\s]?deductible\s+donation\b",
    r"\bcompounding\s+utility\s+value\b(?!\" as a sold benefit)",
)


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    errors: tuple[str, ...]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_markers(text: str, markers: tuple[str, ...], *, label: str) -> list[str]:
    return [f"{label} missing required marker: {marker}" for marker in markers if marker not in text]


def check_prohibited_positive_claims(text: str) -> list[str]:
    errors: list[str] = []
    for pattern in PROHIBITED_POSITIVE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"terms contain prohibited positive economic claim pattern: {pattern}")
    return errors


def validate_terms(terms_path: Path = TERMS_PATH, council_review_path: Path = COUNCIL_REVIEW_PATH) -> GuardResult:
    terms = read_text(terms_path)
    review = read_text(council_review_path)

    errors: list[str] = []
    errors.extend(check_required_markers(terms, REQUIRED_TERMS, label=str(terms_path)))
    errors.extend(check_required_markers(review, REQUIRED_COUNCIL_REVIEW, label=str(council_review_path)))
    errors.extend(check_prohibited_positive_claims(terms))

    if "tax-deductible donations" in terms and "unless counsel approves" not in terms:
        errors.append("tax-deductible language is not explicitly counsel-gated")
    if "future growth is not the thing being sold" not in terms:
        errors.append("future growth is not clearly excluded from consideration")
    if review.lower().count("tightening applied") < 4:
        errors.append("council review must show tightening from all four lenses")

    return GuardResult(ok=not errors, errors=tuple(errors))


def main() -> int:
    result = validate_terms()
    if result.ok:
        print("PMA Patron Engine terms guard: PASS")
        return 0
    for error in result.errors:
        print(error)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
