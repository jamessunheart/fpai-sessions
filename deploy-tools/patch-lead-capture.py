#!/usr/bin/env python3
"""Patch lead-capture-api.py to serve /call page and save qualifying answers."""

with open("/opt/fpai/leads/lead-capture-api.py", "r") as f:
    content = f.read()

# Patch 1: Add /call and /api/leads/call routes to do_GET
old_form_route = '        elif path.path == "/api/leads/form":'
new_routes = '''        elif path.path in ("/call", "/api/leads/call"):
            with open("/opt/fpai/leads/call-page.html") as fp:
                self._send(200, fp.read(), "text/html")

        elif path.path == "/api/leads/form":'''

if old_form_route in content:
    content = content.replace(old_form_route, new_routes)
    print("Patched: Added /call route")
else:
    print("WARNING: Could not find form route to patch")

# Patch 2: Update save_lead to store qualifying_answers
old_save = '''    try:
        db.execute(
            """INSERT OR REPLACE INTO leads
               (name, email, company, phone, source, notes, raw_data, status, score, created_at, updated_at)'''

new_save = '''    # Add qualifying_answers column if needed
    try:
        db.execute("ALTER TABLE leads ADD COLUMN qualifying_answers TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE leads ADD COLUMN message TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        db.execute(
            """INSERT OR REPLACE INTO leads
               (name, email, company, phone, source, notes, raw_data, status, score, created_at, updated_at, qualifying_answers, message)'''

if old_save in content:
    content = content.replace(old_save, new_save)
    print("Patched: save_lead stores qualifying_answers")
else:
    print("WARNING: Could not find save_lead to patch")

# Patch 3: Add qualifying_answers to the VALUES
old_values = '''VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 0, ?, ?)'''.strip()
# Find the actual VALUES pattern
import re
m = re.search(r"VALUES \(\?, \?, \?, \?, \?, \?, \?, 'new', 0, \?, \?\)", content)
if m:
    content = content[:m.start()] + "VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 0, ?, ?, ?, ?)" + content[m.end():]
    print("Patched: VALUES clause updated")

# Patch 4: Update the execute params to include qualifying_answers and message
old_params = '''            (data.get("name"), email, data.get("company"), data.get("phone"),
             data.get("source", "unknown"), data.get("notes", ""), json.dumps(data), now, now)'''

new_params = '''            (data.get("name"), email, data.get("company"), data.get("phone"),
             data.get("source", "unknown"), data.get("notes", ""), json.dumps(data), now, now,
             json.dumps(data.get("qualifying_answers")) if data.get("qualifying_answers") else None,
             data.get("message", ""))'''

if old_params in content:
    content = content.replace(old_params, new_params)
    print("Patched: execute params include qualifying_answers")
else:
    print("WARNING: Could not find execute params")

with open("/opt/fpai/leads/lead-capture-api.py", "w") as f:
    f.write(content)

print("Done. Lead capture API patched.")
