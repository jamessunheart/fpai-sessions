# Voice Interface - Full Potential AI

Emergency deployment project for voice-based AI interface.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Run locally
chainlit run app.py -w

# 4. Open browser
# http://localhost:8000
```

## Project Structure

```
voice-interface/
├── app.py                 # Main Chainlit application
├── config.py              # Configuration and system prompts
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── README.md             # This file
└── IMPLEMENTATION_PLAN.md # Detailed plan and context
```

## Features

- ✅ Voice input (speech-to-text)
- ✅ Text chat (fallback)
- ✅ Image/vision analysis
- ✅ Conversation memory
- ✅ Mobile responsive
- ✅ Action-oriented AI responses

## Deployment

See `IMPLEMENTATION_PLAN.md` for detailed deployment instructions (Railway/Render).

## API Keys Required

- `ANTHROPIC_API_KEY` - Required (from James)
- `DEEPGRAM_API_KEY` - Optional (premium voice)
- `ELEVENLABS_API_KEY` - Optional (voice output)

---

**Status**: In Development  
**Target**: Friday 5pm deployment


