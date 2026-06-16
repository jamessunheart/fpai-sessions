# cal_com Mastery Card

## What it does best
Cal.com is best for scheduling flows where availability, time zones, buffers, routing rules, and confirmation events need to stay consistent across calendars.

## Optimal use patterns (concrete, with examples)
- Treat booking creation as a state transition with confirmation, cancellation, and reschedule states.
- Always carry time zone explicitly. Example: "2026-06-16 15:00 Europe/Athens" rather than a bare local time.
- Use event types for different commitments so duration, buffer, questions, and routing stay predictable.
- Require human review before booking on James's behalf unless an exact approved scheduling rule exists.
- Log booking IDs, attendee identity, time zone, and source intent for reconciliation.

## Anti-patterns (what silently degrades it)
- Booking from ambiguous natural-language times.
- Ignoring buffers, travel time, or James-state constraints.
- Treating a proposed slot as confirmed before Cal.com returns a booking.
- Losing cancellation/reschedule webhook events.
- Using one generic event type for calls with different stakes.

## Effort/parameter settings for this system
Use deterministic validation before any booking action: attendee, event type, exact time zone, duration, and James approval/gate. Calendar writes are higher-stakes than calendar reads.

## Key constraints and hard limits
Codex may build scheduling helpers and prompts, but live bookings that affect James's calendar require explicit route approval unless a future spec grants a narrow auto-booking rule.

## How to detect it's not performing well
Double-bookings appear, attendees receive wrong times, cancellations are missed, James has to manually reconcile the calendar, or booking prompts lack time zone and approval state.

## Last updated + source
Seeded 2026-06-16 from Cal.com scheduling best practices and FPAI attention-flow constraints.

