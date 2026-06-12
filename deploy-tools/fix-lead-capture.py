#!/usr/bin/env python3
"""Fix lead-capture-api.py params to include qualifying_answers and message."""
import re

path = "/opt/fpai/leads/lead-capture-api.py"
with open(path, "r") as f:
    content = f.read()

# Fix 1: VALUES clause needs ?, ? for qualifying_answers and message
old_values = "VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 30, ?, ?)"
new_values = "VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 30, ?, ?, ?, ?)"
if old_values in content:
    content = content.replace(old_values, new_values)
    print("Fixed VALUES clause")

# Also check for score=0 variant  
old_values2 = "VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 0, ?, ?)"
new_values2 = "VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 0, ?, ?, ?, ?)"
if old_values2 in content:
    content = content.replace(old_values2, new_values2)
    print("Fixed VALUES clause (score=0 variant)")

# Fix 2: Find the execute params tuple and add qualifying_answers + message
# Look for the pattern ending with now, now)
pattern = re.compile(
    r'(\(data\.get\("name"\), email, data\.get\("company"\), data\.get\("phone"\),\s+'
    r'data\.get\("source"[^)]*?\), data\.get\("notes"[^)]*?\), json\.dumps\(data\), now, now\))',
    re.DOTALL
)
m = pattern.search(content)
if m:
    old_params = m.group(0)
    new_params = old_params[:-1]  # Remove trailing )
    new_params += ',\n             json.dumps(data.get("qualifying_answers")) if data.get("qualifying_answers") else None,\n             data.get("message", ""))'
    content = content.replace(old_params, new_params)
    print("Fixed execute params")
else:
    print("WARNING: Could not find execute params pattern")
    # Show what we're looking for
    for i, line in enumerate(content.split("\n"), 1):
        if "json.dumps(data)" in line:
            print(f"  Line {i}: {line.strip()}")

with open(path, "w") as f:
    f.write(content)
print("Done")
