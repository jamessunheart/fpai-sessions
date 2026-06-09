#!/usr/bin/env python3
"""Patch the old Aria service to forward webhooks to the new Opus brain."""

# Read the file
with open("/opt/fpai/aria/server.py", "r") as f:
    lines = f.readlines()

# Find the start of telegram_webhook function
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if '@app.post("/telegram/webhook")' in line:
        start_idx = i
    elif start_idx is not None and line.startswith("@app.") and i > start_idx + 1:
        end_idx = i
        break

if start_idx is None:
    print("Could not find telegram_webhook")
    exit(1)

if end_idx is None:
    end_idx = len(lines)

print(f"Found function from line {start_idx} to {end_idx}")

# New function that forwards to aria-command
new_function = '''@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Forward Telegram updates to Opus-powered aria-command service."""
    try:
        update = await request.json()
        logger.info(f"Telegram update received, forwarding to aria-command")
        
        # Forward to new Opus brain
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8750/telegram/webhook",
                json=update
            )
            return response.json()
    except Exception as e:
        logger.error(f"Telegram webhook forward error: {e}")
        return {"ok": False, "error": str(e)}

'''

# Replace the old function
new_lines = lines[:start_idx] + [new_function] + lines[end_idx:]

# Backup and write
with open("/opt/fpai/aria/server.py.bak.forward", "w") as f:
    f.writelines(lines)

with open("/opt/fpai/aria/server.py", "w") as f:
    f.writelines(new_lines)

print("Patched successfully!")


