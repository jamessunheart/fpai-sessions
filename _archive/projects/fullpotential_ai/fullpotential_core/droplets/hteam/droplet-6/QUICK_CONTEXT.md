# Quick Context: What's Happening Here?

## The Big Picture

You're building a **voice-first AI assistant** for James. This isn't just a chatbot - it's designed to be a natural, LIFE-to-LIFE communication interface.

## What Makes This Different?

1. **Voice-First**: Designed for speaking, not typing
2. **Action-Oriented**: AI executes and reports, doesn't just chat
3. **Mobile**: Works on phone for on-the-go access
4. **Vision**: Can see images/screens you share
5. **Focus**: TIER 1 priorities only (revenue, delivery, deployment)

## The Stack (Simple!)

- **Chainlit**: Handles the chat UI and WebSocket communication
- **Claude API**: Provides the AI intelligence (Claude Sonnet 4)
- **Web Speech API**: Browser converts speech → text (FREE)
- **Python**: Backend language

## How It Works

```
You speak → Browser converts to text → Chainlit server → Claude API → Response → You see/hear
```

## The Timeline

- **Phase 1 (2h)**: Basic chat working
- **Phase 2 (2h)**: Voice input added
- **Phase 3 (1-2h)**: Mobile optimized
- **Phase 4 (1-2h)**: Vision/image support

**Total**: 4-6 hours to full deployment

## Key Files

- `app.py` - Main application (where the magic happens)
- `config.py` - System prompts and configuration
- `requirements.txt` - Dependencies

## What You Need

1. Claude API key from James
2. Python 3.11+
3. Internet connection
4. Modern browser (Chrome/Edge best for voice)

## Success = Friday 5pm

By Friday evening, James should be able to:
- Speak to the AI naturally
- Share screens/images for analysis
- Get action-oriented responses
- Use it from his phone

That's it! Simple concept, powerful result.

---

**Next Step**: Read `IMPLEMENTATION_PLAN.md` for full technical details, then we'll start building!


