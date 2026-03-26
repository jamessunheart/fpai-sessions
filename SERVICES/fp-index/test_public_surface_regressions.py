"""
Regression checks for public surfaces.

These are lightweight source-level guards for the bugs fixed in the
shareable homepage work:
1. Public signal/feed rendering must escape untrusted content.
2. Allocation history must not be written from the public GET endpoint.
3. Homepage top signals should use the dedicated top-signals endpoint.
"""

from pathlib import Path


MAIN_PY = Path(__file__).parent / "app" / "main.py"


def read_main() -> str:
    return MAIN_PY.read_text()


def check(label: str, ok: bool) -> None:
    if ok:
        print(f"PASS: {label}")
    else:
        print(f"FAIL: {label}")
        raise SystemExit(1)


def main() -> None:
    source = read_main()

    check(
        "homepage uses server-side top-signals endpoint",
        "/api/v1/feed/top?limit=5&since_hours=24" in source,
    )
    check(
        "homepage has client-side escaping helper",
        "function esc(value)" in source and "function safeUrl(value)" in source,
    )
    check(
        "intelligence page has client-side escaping helper",
        "function escHtml(value)" in source and "function safePublicUrl(value)" in source,
    )
    check(
        "signal page escapes summary content",
        "summary_body = html_escape(raw_summary)" in source,
    )
    check(
        "allocation GET endpoint no longer writes history rows",
        'session.add(AllocationHistoryRow(' not in source.split('@app.get("/api/v1/invest/allocation")', 1)[1].split('@app.get("/api/v1/invest/report")', 1)[0],
    )
    check(
        "scheduled allocation snapshot helper exists",
        "async def _snapshot_allocation_history()" in source,
    )

    print("All public surface regression checks passed.")


if __name__ == "__main__":
    main()
