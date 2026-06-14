#!/usr/bin/env python3
"""Update main.py to serve booking.html at /book and /booking routes."""

FILE = "/opt/fpai/apps/zen-village/app/main.py"

with open(FILE, "r") as f:
    lines = f.readlines()

# Find the old booking_page route
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if '@app.get("/booking"' in line:
        start_idx = i
    if start_idx is not None and i > start_idx + 5 and '@app.get(' in line:
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    new_route_lines = [
        '\n',
        '@app.get("/book", response_class=HTMLResponse)\n',
        '@app.get("/booking", response_class=HTMLResponse)\n',
        'async def booking_page():\n',
        '    """Dedicated booking page with payment methods"""\n',
        '    booking_path = BASE_DIR / "frontend" / "public" / "booking.html"\n',
        '    if booking_path.exists():\n',
        '        return FileResponse(booking_path, media_type="text/html")\n',
        '    return RedirectResponse(url="/")\n',
        '\n',
        '\n',
    ]
    
    new_lines = lines[:start_idx] + new_route_lines + lines[end_idx:]
    
    with open(FILE, "w") as f:
        f.writelines(new_lines)
    print(f"Replaced booking route (lines {start_idx+1}-{end_idx})")
    print("Added /book and /booking routes serving booking.html")
else:
    print(f"Could not find booking route. start={start_idx}, end={end_idx}")

# Verify
with open(FILE, "r") as f:
    content = f.read()

checks = [
    ('/book route', '"/book"' in content),
    ('/booking route', '"/booking"' in content),
    ('booking.html reference', 'booking.html' in content),
    ('FileResponse for booking', 'booking_path' in content),
]
for name, result in checks:
    print(f"  {'OK' if result else 'FAIL'} {name}")
