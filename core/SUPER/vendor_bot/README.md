# SUPER vendor bot — the Super Agent's own voice
Why: a message sent from James's personal WhatsApp is James speaking, and needs his approval each time. A message from the Super Agent's own WhatsApp Business number is the Super Agent speaking — disclosed as AI, bound by the Card — and can run the 3-message flow, log every reply verbatim, classify, and hand off, without a human plank in the middle.

What James does once: get a WhatsApp Business number + token from Meta (free tier covers this), set 4 env vars, run the bot, point the webhook at it. Then: `python3 vendor_bot.py start 50663626524 "La Cocinona de Pueblo" 001`.

What the bot will never do: book, pay, mint, quote anything about SUPER beyond REDEMPTION.md, go above 100 SUPER, add colones, message a number it wasn't started with, send more than one follow-up, or hide a no. Unknown questions get "se lo consulto a James." Every handoff pings James's number.

Dry run (no token): messages print instead of sending. Test: `python3 -c "import vendor_bot as v; print(v.MSG['m2'].format(redemption=v.redemption_line()))"`.
