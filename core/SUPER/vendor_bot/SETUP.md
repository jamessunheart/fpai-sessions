# Give the Super Agent its own number — 5 steps, ~20 minutes, free tier

1. Meta for Developers (developers.facebook.com) → My Apps → Create App → type "Business" → add the WhatsApp product.
   (If FP Ventures already has a Meta Business account from the ads work, use it; otherwise the wizard creates one.)
2. WhatsApp → API Setup: Meta gives you a free TEST number immediately (good for up to 5 recipient numbers you verify — enough for the first 5 vendors).
   For a real number later: "Add phone number" → a new SIM/VoIP number the Super Agent owns. It must NOT be a number already on personal WhatsApp.
   Copy: Phone number ID, and generate a permanent token (Business Settings → System Users → Add → assign the app → Generate token, whatsapp_business_messaging + whatsapp_business_management).
3. On the server (brain.sunheart.com or any host with a public URL):
     git clone / copy core/SUPER to /opt/fpos/core/SUPER ; cd vendor_bot ; cp .env.example .env ; fill it
     pip install flask requests ; sudo cp super-vendor-bot.service /etc/systemd/system/ ; sudo systemctl enable --now super-vendor-bot
4. Meta → WhatsApp → Configuration → Webhook: URL https://<host>/webhook, verify token = WA_VERIFY_TOKEN, subscribe to "messages".
5. Start the first conversation on the bot's own line:
     python3 vendor_bot.py start 50627724381 "Cafetería Antojos de Maíz" 001
   Then `python3 vendor_bot.py status` any time; replies land in VENDOR_LOG.md verbatim and James gets a WhatsApp ping at every close.

Note on the test number: Meta's test number requires each recipient to be added to the allowed list first (API Setup → "To" → Manage phone number list) and they must accept — fine for 5 vendors, and honest: they opt in before the bot speaks.
What the Super Agent cannot do for you: create the Meta account or accept its terms. That is a human signature. Everything after it is ready.

## POLICY FACTS (researched 2026-09-03) — these change how the bot may open
- Business-initiated messages (anyone who hasn't written to you first) MUST be an approved TEMPLATE, test number included. A cold intro with a question will be classed Marketing (~$0.085/msg; test number free). Free-form text only inside the 24h window that opens when THEY reply. Error 131047 if you try free-form first.
- WhatsApp Business Policy: message only people who gave you their number AND opted in; provide opt-out. Numbers scraped from directories/Tripadvisor are NOT opt-in. So the bot must NOT cold-message strangers from its own line — that would be a rule bypassed, not a bridge built.
- The honest bridge: a HUMAN makes first contact (in person at the feria, a phone call, or James's own message) and gets consent to be messaged; the bot then runs M2/M3 inside the 24h window. Or the person messages the bot's number first (a printed card with the number + "escríbanos 'SUPER'").
- Test number: 5 recipients max, each must enter a confirmation code — consent by design. Permanent token via System User with whatsapp_business_messaging + whatsapp_business_management. Real number: must not be on personal WhatsApp; 250 recipients/day unverified.
- From 1 Oct 2026 free-form replies inside the window may become billable.
→ vendor_bot M1 is now an OPT-IN CONFIRMATION template, not a cold pitch. Change in vendor_bot.py: `start` is only allowed with `--consented "<how consent was obtained>"`.
