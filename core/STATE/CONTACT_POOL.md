# Contact Pool

Contact pool rows are private pre-outreach records. They are not public-agent context
and they do not authorize outreach by themselves.

## Pre-Profiling

Before first contact, `tools/outreach/pre_profiler.py` builds a private
`brain_index.contact_profiles` row from public sources only:

- James notes from `contact_pool.notes` are highest-confidence context.
- Public source hints in `url_hints` may be fetched respectfully at no more than
  five profile fetches per minute.
- Search results may add only public profile URLs. Paid databases, login-gated
  pages, private groups, secrets, and scraped private data are out of bounds.
- Sensitive personal details such as health, family, and financial information
  are filtered from stored notes.
- The profile stores a short summary, two or three specific resonance points,
  a suggested subject, and a suggested first message.

The profile seeds the AI conversation context and the draft outreach packet, but
it does not send anything. Live sends remain gated by the existing outreach
controls and James approval.
