#!/usr/bin/env python3
path = "/opt/fpai/leads/lead-capture-api.py"
with open(path, "r") as f:
    content = f.read()

old = """            (
                data.get("name", ""),
                email,
                data.get("company", ""),
                data.get("phone", ""),
                data.get("source", "web_form"),
                data.get("message", ""),
                json.dumps(data),
                now, now,
            ),"""

new = """            (
                data.get("name", ""),
                email,
                data.get("company", ""),
                data.get("phone", ""),
                data.get("source", "web_form"),
                data.get("notes", data.get("message", "")),
                json.dumps(data),
                now, now,
                json.dumps(data.get("qualifying_answers")) if data.get("qualifying_answers") else None,
                data.get("message", ""),
            ),"""

if old in content:
    content = content.replace(old, new)
    print("Fixed: params now include qualifying_answers and message")
else:
    print("ERROR: Could not find params block")

with open(path, "w") as f:
    f.write(content)
