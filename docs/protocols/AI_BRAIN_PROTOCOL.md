# AI Brain Protocol v1.0

**Last Updated:** December 1, 2025  
**Purpose:** Ensure the AI Brain always uses the latest and most capable AI models

---

## Core Principle

**ALWAYS USE THE LATEST MODELS** - The AI Brain is the central intelligence of the FPAI system. It must use the most capable models available to provide the best reasoning, analysis, and decision-making.

---

## Current Model Configuration

### Primary Model (Default)
- **Provider:** Anthropic
- **Model:** `claude-opus-4-5-20251101` (Claude Opus 4.5)
- **Released:** November 24, 2025
- **Use For:** Complex reasoning, system decisions, critical analysis

### Secondary Models
| Provider | Model | Use Case |
|----------|-------|----------|
| Anthropic | `claude-sonnet-4-20250514` | Fast responses, routine tasks |
| OpenAI | `gpt-5.1` | Alternative reasoning |
| Google | `gemini-2.5-pro` | Multimodal tasks |
| xAI | `grok-4-fast-reasoning` | Real-time analysis |
| Meta | `llama-3.3-70b` | Local/offline fallback |

### Local Fallback
- **Ollama:** `llama3.2` (3B) - For when cloud APIs are unavailable

---

## Model Selection Rules

1. **Default to Opus 4.5** for all system intelligence tasks
2. **Use Sonnet 4** for high-volume, lower-complexity tasks (cost optimization)
3. **Use Haiku** only for simple parsing/formatting tasks
4. **Fallback to Ollama** if all cloud providers fail

---

## Update Protocol

### When to Update Models
1. New major model release from Anthropic (Claude 5, etc.)
2. Significant capability improvements announced
3. Cost/performance ratio improvements

### How to Update
1. Test new model via direct API call
2. Update `PROVIDERS` dict in `/opt/fpai/ai-brain/main.py`
3. Restart AI Brain: `systemctl restart ai-brain`
4. Verify via health check: `curl http://localhost:8101/health`

### Model Naming Convention
- Anthropic: `claude-{tier}-{version}-{date}` (e.g., `claude-opus-4-5-20251101`)
- OpenAI: `gpt-{version}` (e.g., `gpt-5.1`)
- Google: `gemini-{version}` (e.g., `gemini-2.5-pro`)

---

## API Keys Location

All API keys stored in: `/opt/fpai/ai-brain/api_keys.env`

Required keys:
- `ANTHROPIC_API_KEY` - Primary (Claude)
- `OPENAI_API_KEY` - Secondary
- `XAI_API_KEY` - Optional
- `TOGETHER_API_KEY` - Optional

---

## Monitoring

### Health Check
```bash
curl http://localhost:8101/health
```

### Test Generation
```bash
curl -X POST http://localhost:8101/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "provider": "anthropic"}'
```

### Check Current Models
```bash
curl http://localhost:8101/ | jq .models
```

---

## Cost Considerations

| Model | Input Cost | Output Cost | When to Use |
|-------|------------|-------------|-------------|
| Opus 4.5 | $15/M | $75/M | Critical decisions |
| Sonnet 4 | $3/M | $15/M | Standard tasks |
| Haiku 3.5 | $0.25/M | $1.25/M | Simple parsing |

**Budget Rule:** Use the most capable model that fits the task. Don't cheap out on critical intelligence.

---

## Emergency Fallback Chain

1. Anthropic (Claude Opus 4.5)
2. OpenAI (GPT-5.1)
3. Google Vertex (Gemini 2.5 Pro)
4. xAI (Grok 4)
5. Together (Llama 3.3 70B)
6. Local Ollama (Llama 3.2)

---

## Server Location

- **AI Brain Service:** AI Server (162.0.208.88)
- **Port:** 8101
- **Service:** `ai-brain.service`

---

**Remember:** The AI Brain is the nervous system of FPAI. Keep it running on the best available intelligence.

























