"""CLI for tool mastery cards."""

from __future__ import annotations

import argparse

from .learn import learn_tool, refresh_all


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m curator.tool_mastery")
    sub = parser.add_subparsers(dest="cmd", required=True)

    learn = sub.add_parser("learn")
    learn.add_argument("tool_name")
    learn.add_argument("source")
    learn.add_argument("--force", action="store_true")

    sub.add_parser("refresh-all")
    args = parser.parse_args()

    if args.cmd == "learn":
        path = learn_tool(args.tool_name, args.source, force=args.force)
        print(f"Mastery card created for {args.tool_name}. Review at {path}")
        return 0
    refreshed = refresh_all()
    print(f"Mastery cards refreshed: {len(refreshed)}")
    for path in refreshed:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

