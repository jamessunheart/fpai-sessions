#!/bin/bash
# Calendar Integration — Cal.com API
# Enables: check availability, book calls, list events, create event types
#
# Setup: Set CAL_API_KEY in /opt/fpai/cora-loop/.env
#   1. Sign up at https://cal.com (free tier)
#   2. Go to Settings > Developer > API Keys
#   3. Create a key and add: CAL_API_KEY=cal_live_xxxxx
#
# Usage:
#   calendar.sh status           — Check API connection
#   calendar.sh availability     — Show available slots (next 7 days)
#   calendar.sh book <name> <email> <datetime> [notes]  — Book a call
#   calendar.sh events [days]    — List upcoming events
#   calendar.sh types            — List event types (meeting types)

set -euo pipefail

source /opt/fpai/cora-loop/.env 2>/dev/null || true
CAL_API_KEY="${CAL_API_KEY:-}"
CAL_BASE="https://api.cal.com/v1"

if [ -z "$CAL_API_KEY" ]; then
    echo "ERROR: CAL_API_KEY not set in /opt/fpai/cora-loop/.env"
    echo ""
    echo "Setup instructions:"
    echo "  1. Sign up at https://cal.com (free — no card required)"
    echo "  2. Settings > Developer > API Keys > Create"
    echo "  3. Add to /opt/fpai/cora-loop/.env: CAL_API_KEY=cal_live_xxxxx"
    echo "  4. Create a 'Full Potential Session' event type (30 or 60 min)"
    exit 1
fi

cal_api() {
    local method="$1" endpoint="$2" data="${3:-}"
    local sep="?"
    [[ "$endpoint" == *"?"* ]] && sep="&"
    local url="${CAL_BASE}${endpoint}${sep}apiKey=${CAL_API_KEY}"
    
    if [ "$method" = "GET" ]; then
        curl -s "$url" -H "Content-Type: application/json"
    else
        curl -s -X "$method" "$url" -H "Content-Type: application/json" -d "$data"
    fi
}

cmd_status() {
    echo "Testing Cal.com API connection..."
    result=$(cal_api GET "/event-types")
    if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Connected. {len(d.get(\"event_types\",d.get(\"data\",[])))} event type(s) found.')" 2>/dev/null; then
        echo "Calendar integration: ACTIVE"
    else
        echo "Connection failed. Response: $result"
        exit 1
    fi
}

cmd_availability() {
    local days="${1:-7}"
    local start=$(date -u +"%Y-%m-%dT00:00:00Z")
    local end=$(date -u -d "+${days} days" +"%Y-%m-%dT23:59:59Z" 2>/dev/null || date -u -v+${days}d +"%Y-%m-%dT23:59:59Z")
    
    # Get event types first
    types=$(cal_api GET "/event-types")
    event_type_id=$(echo "$types" | python3 -c "
import sys, json
d = json.load(sys.stdin)
types = d.get('event_types', d.get('data', []))
if types:
    print(types[0].get('id', ''))
" 2>/dev/null)
    
    if [ -z "$event_type_id" ]; then
        echo "No event types found. Create one at cal.com first."
        exit 1
    fi
    
    result=$(cal_api GET "/slots?eventTypeId=${event_type_id}&startTime=${start}&endTime=${end}")
    echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
slots = d.get('slots', {})
total = 0
if isinstance(slots, dict) and slots:
    for date in sorted(slots.keys()):
        times = slots[date]
        total += len(times)
        print('  {}:'.format(date))
        for t in times[:5]:
            ts = t.get('time', t) if isinstance(t, dict) else t
            print('    {}'.format(ts))
        if len(times) > 5:
            print('    ... +{} more'.format(len(times) - 5))
    print()
    print('  Total available slots: {}'.format(total))
else:
    print('  No available slots found.')
    if 'message' in d:
        print('  API message: {}'.format(d['message']))
" 2>/dev/null || echo "$result"
}

cmd_book() {
    local name="$1" email="$2" datetime="$3" notes="${4:-Full Potential Session}"
    
    # Get first event type
    types=$(cal_api GET "/event-types")
    event_type_id=$(echo "$types" | python3 -c "
import sys, json
d = json.load(sys.stdin)
types = d.get('event_types', d.get('data', []))
if types:
    print(types[0].get('id', ''))
" 2>/dev/null)
    
    if [ -z "$event_type_id" ]; then
        echo "No event types found."
        exit 1
    fi
    
    payload=$(python3 -c "
import json
print(json.dumps({
    'eventTypeId': int('${event_type_id}'),
    'start': '${datetime}',
    'responses': {
        'name': '${name}',
        'email': '${email}',
        'notes': '${notes}'
    },
    'metadata': {},
    'timeZone': 'Pacific/Honolulu',
    'language': 'en'
}))
")
    
    result=$(cal_api POST "/bookings" "$payload")
    echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'id' in d or 'uid' in d:
    booking = d
    print(f'Booking confirmed!')
    print(f'  ID: {booking.get(\"id\", booking.get(\"uid\"))}')
    print(f'  Start: {booking.get(\"startTime\", booking.get(\"start\"))}')
    print(f'  Attendee: {booking.get(\"attendees\", [{}])[0].get(\"email\", \"\")}')
    print(f'  Status: {booking.get(\"status\", \"confirmed\")}')
else:
    print(f'Booking response: {json.dumps(d, indent=2)[:500]}')
" 2>/dev/null || echo "$result"
}

cmd_events() {
    local days="${1:-7}"
    result=$(cal_api GET "/bookings")
    echo "$result" | python3 -c "
import sys, json
from datetime import datetime, timedelta, timezone
d = json.load(sys.stdin)
bookings = d.get('bookings', d.get('data', []))
cutoff = datetime.now(timezone.utc) + timedelta(days=${days})
upcoming = []
for b in bookings:
    start = b.get('startTime', b.get('start', ''))
    if start and start > datetime.now(timezone.utc).isoformat():
        upcoming.append(b)
if not upcoming:
    print('  No upcoming events in the next ${days} days.')
else:
    for b in sorted(upcoming, key=lambda x: x.get('startTime', x.get('start', '')))[:10]:
        title = b.get('title', 'Meeting')
        start = b.get('startTime', b.get('start', ''))[:16]
        status = b.get('status', '?')
        attendees = ', '.join(a.get('email','') for a in b.get('attendees', []))
        print(f'  {start} | {title} | {attendees} | {status}')
print(f'\n  Total upcoming: {len(upcoming)}')
" 2>/dev/null || echo "$result"
}

cmd_types() {
    result=$(cal_api GET "/event-types")
    echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
types = d.get('event_types', d.get('data', []))
if not types:
    print('  No event types. Create one at cal.com:')
    print('    - Full Potential Session (60 min)')
    print('    - Discovery Call (30 min)')
else:
    for t in types:
        print(f'  [{t.get(\"id\")}] {t.get(\"title\", \"?\")} ({t.get(\"length\", \"?\")} min) — {t.get(\"slug\", \"\")}')
" 2>/dev/null || echo "$result"
}

case "${1:-help}" in
    status)       cmd_status ;;
    availability) cmd_availability "${2:-7}" ;;
    book)         cmd_book "${2:?name required}" "${3:?email required}" "${4:?datetime required}" "${5:-}" ;;
    events)       cmd_events "${2:-7}" ;;
    types)        cmd_types ;;
    *)
        echo "Calendar Integration (Cal.com)"
        echo "  status           — Test API connection"
        echo "  availability     — Show available slots"
        echo "  book <name> <email> <datetime> [notes] — Book a call"
        echo "  events [days]    — List upcoming events"
        echo "  types            — List event types"
        ;;
esac
