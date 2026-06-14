# Setup Instructions

## Quick Start (Local Development)

### 1. Install Dependencies

```bash
cd voice-interface
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the `voice-interface` directory:

```bash
# Copy the example (if it exists) or create manually
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Get your API key from**: James (or Anthropic dashboard)

### 3. Run the Application

```bash
chainlit run app.py -w
```

The `-w` flag enables auto-reload on file changes.

### 4. Open in Browser

Navigate to: `http://localhost:8000`

You should see the chat interface!

## Testing Phase 1

1. Type a message in the chat
2. You should receive a response from "Full Potential AI"
3. Responses should be short (1-3 sentences) and action-oriented
4. Try multiple messages - conversation context should persist

## Common Issues

### "ANTHROPIC_API_KEY not found"
- Make sure `.env` file exists in `voice-interface/` directory
- Check that the key is correctly formatted (starts with `sk-ant-`)
- Restart the server after creating `.env`

### "Module not found" errors
- Run `pip install -r requirements.txt` again
- Make sure you're in the correct directory
- Check Python version (need 3.11+)

### Port already in use
- Change port: `chainlit run app.py -w --port 8001`
- Or kill the process using port 8000

## Next Steps

After Phase 1 works:
- Phase 2: Add voice input (Web Speech API)
- Phase 3: Mobile optimization
- Phase 4: Vision/image support

---

**Phase 1 Status**: ✅ Ready to test!
