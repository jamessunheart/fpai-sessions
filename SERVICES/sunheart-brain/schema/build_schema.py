#!/usr/bin/env python3
"""
Sunheart Brain — AppFlowy schema driver.

Fork of docs/zen-village/schema/build_schema.py — same engine, different spec.
Creates the 5 Sunheart Brain databases + fields via AppFlowy Cloud's REST API.
Idempotent: safe to re-run.

Runs on Secondary (162.0.208.88) after `bootstrap.sh` has provisioned the
owner and returned the workspace_id.

Usage:
    python3 build_schema.py                     # create everything missing
    python3 build_schema.py --dry-run
    python3 build_schema.py --only "01 · Notes"
    python3 build_schema.py --purge-defaults    # trash default To-dos/Grid pages first
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import urllib.error
import urllib.request


BASE      = os.environ.get("SH_APPFLOWY_BASE", "https://brain.sunheart.com")
SECRETS   = Path(os.environ.get("SH_SECRETS", "/root/sh-brain-secrets/brain.env"))
SCHEMA    = Path(__file__).with_name("sh_schema.json")
SPACE     = os.environ.get("SH_SPACE", "General")
OWNER_KEY = "SH_OWNER_EMAIL"
PASS_KEY  = "SH_OWNER_PASSWORD"

FIELD_TYPE = {
    "text":           0,
    "long_text":      0,
    "number":         1,
    "date":           2,
    "single_select":  3,
    "multi_select":   4,
    "checkbox":       5,
    "url":            6,
    "checklist":      7,
    "created_time":   9,
    "relation":      10,
    "time":          13,
    "file_attachment":14,
    "person":        15,
}

COLOR_PALETTE = [
    "Purple", "Pink", "LightPink", "Orange", "Yellow",
    "Lime",   "Green", "Aqua",     "Blue",   "Maroon",
]


def load_env() -> dict[str, str]:
    if not SECRETS.exists():
        raise SystemExit(f"secrets file not found: {SECRETS}")
    env: dict[str, str] = {}
    for line in SECRETS.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def http_request(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, Any]:
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def login(email: str, password: str) -> str:
    status, body = http_request(
        "POST", "/gotrue/token?grant_type=password",
        body={"email": email, "password": password},
    )
    if status != 200 or "access_token" not in body:
        raise SystemExit(f"login failed: {status} {body}")
    return body["access_token"]


def get_workspace_id(token: str) -> str:
    status, body = http_request("GET", "/api/workspace", token)
    return body["data"][0]["workspace_id"]


def get_folder(token: str, workspace_id: str) -> dict:
    status, body = http_request("GET", f"/api/workspace/{workspace_id}/folder?depth=3", token)
    return body["data"]


def find_space(folder: dict, name: str = "General") -> dict:
    for child in folder.get("children", []) or []:
        if child.get("is_space") and child.get("name") == name:
            return child
    raise SystemExit(f"space '{name}' not found under workspace root")


def find_page_by_name(parent: dict, name: str) -> dict | None:
    for child in parent.get("children", []) or []:
        if child.get("name") == name:
            return child
    return None


def create_grid_page(token: str, workspace_id: str, parent_view_id: str, name: str) -> tuple[str, str]:
    status, body = http_request(
        "POST", f"/api/workspace/{workspace_id}/page-view", token,
        {"parent_view_id": parent_view_id, "layout": 1, "name": name},
    )
    if status != 200 or body.get("code") != 0:
        raise RuntimeError(f"create page '{name}' failed: {status} {body}")
    return body["data"]["view_id"], body["data"]["database_id"]


def list_fields(token: str, workspace_id: str, db_id: str) -> list[dict]:
    status, body = http_request("GET", f"/api/workspace/{workspace_id}/database/{db_id}/fields", token)
    return body.get("data", []) if isinstance(body, dict) else []


def add_field(token: str, workspace_id: str, db_id: str, name: str, field_type: int, type_option_data: dict | None = None) -> str:
    payload: dict[str, Any] = {"name": name, "field_type": field_type}
    if type_option_data is not None:
        payload["type_option_data"] = type_option_data
    status, body = http_request(
        "POST", f"/api/workspace/{workspace_id}/database/{db_id}/fields", token, payload,
    )
    if status != 200 or body.get("code") != 0:
        raise RuntimeError(f"add field '{name}' failed: {status} {body}")
    return body["data"]


def select_type_option(options: list[str]) -> dict:
    rendered = [
        {"id": uuid.uuid4().hex[:8], "name": opt, "color": COLOR_PALETTE[i % len(COLOR_PALETTE)]}
        for i, opt in enumerate(options)
    ]
    return {"content": json.dumps({"options": rendered, "disable_color": False})}


def relation_option(target_db_id: str) -> dict:
    return {"content": json.dumps({"database_id": target_db_id})}


def move_to_trash(token: str, workspace_id: str, view_id: str):
    http_request("POST", f"/api/workspace/{workspace_id}/page-view/{view_id}/move-to-trash", token)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--purge-defaults", action="store_true")
    args = ap.parse_args()

    env = load_env()
    email = env.get(OWNER_KEY, "james.rick.stinson@gmail.com")
    password = env.get(PASS_KEY)
    if not password:
        raise SystemExit(f"{PASS_KEY} missing in secrets file")

    schema = json.loads(SCHEMA.read_text())

    print(f"→ logging in as {email}")
    token = login(email, password)

    workspace_id = get_workspace_id(token)
    print(f"→ workspace_id = {workspace_id}")

    folder = get_folder(token, workspace_id)
    space = find_space(folder, SPACE)
    print(f"→ space '{SPACE}' view_id = {space['view_id']}")

    if args.purge_defaults:
        for child in space.get("children", []) or []:
            if child["name"] in ("To-dos", "Grid") or child["name"].startswith("TEST_"):
                print(f"  trashing {child['name']} ({child['view_id']})")
                if not args.dry_run:
                    move_to_trash(token, workspace_id, child["view_id"])
        folder = get_folder(token, workspace_id)
        space = find_space(folder, SPACE)

    name_to_db_id: dict[str, str] = {}
    deferred: list[tuple[str, str, str, str]] = []

    for db in schema["databases"]:
        db_name = db["name"]
        if args.only and db_name != args.only:
            continue
        existing = find_page_by_name(space, db_name)
        if existing:
            print(f"→ '{db_name}' already exists; reusing view={existing['view_id'][:8]}")
            view_id = existing["view_id"]
            _, db_list = http_request("GET", f"/api/workspace/{workspace_id}/database", token)
            db_id = None
            for d in db_list.get("data", []):
                for v in d.get("views", []):
                    if v["view_id"] == view_id:
                        db_id = d["id"]
                        break
            if not db_id:
                print(f"  ! could not find database_id for existing view; skipping fields")
                continue
        else:
            print(f"→ creating '{db_name}'")
            if args.dry_run:
                continue
            view_id, db_id = create_grid_page(token, workspace_id, space["view_id"], db_name)
        name_to_db_id[db_name] = db_id

        existing_names = {f["name"] for f in list_fields(token, workspace_id, db_id)}
        for field in db["fields"]:
            fname = field["name"]
            if fname in existing_names:
                print(f"    · field '{fname}' exists — skip")
                continue
            ftype_key = field["type"]
            if ftype_key == "relation":
                target = field.get("relates_to")
                if target in name_to_db_id:
                    if args.dry_run:
                        print(f"    + relation '{fname}' → {target} [DRY]")
                        continue
                    add_field(token, workspace_id, db_id, fname, 10, relation_option(name_to_db_id[target]))
                    print(f"    + relation '{fname}' → {target}")
                else:
                    deferred.append((db_name, db_id, fname, target))
                    print(f"    · deferring relation '{fname}' (target '{target}' not built yet)")
                continue
            ft_id = FIELD_TYPE[ftype_key]
            type_option: dict | None = None
            if ftype_key in ("single_select", "multi_select"):
                type_option = select_type_option(field["options"]) if field.get("options") else select_type_option([])
            elif ftype_key == "date" and field.get("auto_on_create"):
                ft_id = FIELD_TYPE["created_time"]
                type_option = None
            if args.dry_run:
                print(f"    + {fname} ({ftype_key}) [DRY]")
                continue
            add_field(token, workspace_id, db_id, fname, ft_id, type_option)
            print(f"    + {fname} ({ftype_key})")
            time.sleep(0.05)

    print("\n=== Second pass: deferred relations ===")
    for db_name, db_id, fname, target in deferred:
        if target not in name_to_db_id:
            print(f"  ! {db_name}.{fname} — target '{target}' still missing")
            continue
        existing_names = {f["name"] for f in list_fields(token, workspace_id, db_id)}
        if fname in existing_names:
            print(f"  · {db_name}.{fname} exists — skip")
            continue
        if args.dry_run:
            print(f"  + {db_name}.{fname} → {target} [DRY]")
            continue
        add_field(token, workspace_id, db_id, fname, 10, relation_option(name_to_db_id[target]))
        print(f"  + {db_name}.{fname} → {target}")

    print("\n=== DONE ===")
    print(json.dumps({"workspace_id": workspace_id, "databases": name_to_db_id}, indent=2))


if __name__ == "__main__":
    main()
