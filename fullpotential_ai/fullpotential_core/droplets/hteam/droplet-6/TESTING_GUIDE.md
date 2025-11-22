# Testing Guide - Phase 1

## Prerequisites

Before testing, you need:
1. **Python 3.11+** installed
2. **Anthropic API Key** from James (format: `sk-ant-...`)
3. **Internet connection** (for Claude API calls)

---

## Step-by-Step Testing

### Step 1: Install Dependencies

Open terminal/command prompt in the `voice-interface` directory:

```bash
cd voice-interface
pip install -r requirements.txt
```

**Expected output**: Packages install successfully (chainlit, anthropic, python-dotenv)

**If you get errors**:
- Make sure Python 3.11+ is installed: `python --version`
- Try: `pip3 install -r requirements.txt`
- On Windows, you might need: `python -m pip install -r requirements.txt`

---

### Step 2: Set Up Environment Variables

Create a `.env` file in the `voice-interface` directory:

**Option A: Create manually**
1. Create a new file named `.env` (exactly this name, with the dot)
2. Add this line:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   ```
3. Replace `sk-ant-your-actual-key-here` with your real API key

**Option B: Copy from example** (if .env.example exists)
```bash
# On Mac/Linux
cp .env.example .env

# On Windows PowerShell
Copy-Item .env.example .env
```

Then edit `.env` and add your API key.

**Important**: 
- The `.env` file should be in the same directory as `app.py`
- Never commit `.env` to git (it's in .gitignore)

---

### Step 3: Start the Application

Run this command:

```bash
chainlit run app.py -w
```

The `-w` flag enables auto-reload (server restarts when you change code).

**Expected output**:
```
╭─────────────────────────────────────────────────────────╮
│                                                          │
│  Chainlit                                                │
│                                                          │
│  Your app is running at http://localhost:8000           │
│                                                          │
╰─────────────────────────────────────────────────────────╯
```

**If you get an error**:
- `ANTHROPIC_API_KEY not found`: Check your `.env` file exists and has the key
- `Module not found`: Run `pip install -r requirements.txt` again
- `Port already in use`: Change port with `chainlit run app.py -w --port 8001`

---

### Step 4: Open in Browser

1. Open your web browser (Chrome, Edge, or Firefox recommended)
2. Navigate to: `http://localhost:8000`
3. You should see the Chainlit chat interface

**What you should see**:
- A chat interface with a welcome message from "Full Potential AI"
- A text input box at the bottom
- A send button

---

### Step 5: Test Basic Chat

**Test 1: Simple Message**
1. Type: `Hello, what can you help me with?`
2. Click Send (or press Enter)
3. **Expected**: You get a response from "Full Potential AI" in 1-3 sentences

**Test 2: Conversation Context**
1. Type: `What's blocking TIER 1 today?`
2. Wait for response
3. Type: `Can you elaborate on that?`
4. **Expected**: AI remembers the previous message about TIER 1

**Test 3: Action-Oriented Response**
1. Type: `What should I focus on right now?`
2. **Expected**: AI gives short, actionable response (not a long essay)

**Test 4: Multiple Turns**
1. Have a conversation with 3-4 back-and-forth messages
2. **Expected**: Context is maintained throughout

---

## What to Look For (Success Indicators)

✅ **Working correctly if**:
- You get responses within 2-5 seconds
- Responses are short (1-3 sentences)
- AI remembers previous messages
- Responses feel action-oriented (not just chit-chat)
- No error messages appear

❌ **Not working if**:
- You see "Error: API key invalid" or similar
- Responses take more than 10 seconds
- You get Python traceback errors
- Browser shows "Connection refused"

---

## Troubleshooting

### Problem: "ANTHROPIC_API_KEY not found"

**Solution**:
1. Check `.env` file exists in `voice-interface/` directory
2. Make sure the key starts with `sk-ant-`
3. No quotes around the key value
4. Restart the server after creating `.env`

### Problem: "Module not found: chainlit"

**Solution**:
```bash
pip install chainlit anthropic python-dotenv
```

### Problem: Port 8000 already in use

**Solution**:
```bash
chainlit run app.py -w --port 8001
```
Then open `http://localhost:8001`

### Problem: Slow responses

**Possible causes**:
- Slow internet connection
- Claude API rate limits
- First request might be slower (cold start)

**Solution**: Wait a few seconds, try again. If persistent, check API key has credits.

### Problem: Responses are too long

**This is expected in Phase 1** - we'll optimize in Phase 2. But responses should still be relatively short (1-3 sentences).

---

## Testing Checklist

Before moving to Phase 2, verify:

- [ ] Can send text messages
- [ ] Receive responses from AI
- [ ] Conversation context works (AI remembers previous messages)
- [ ] Responses are action-oriented (not just chatting)
- [ ] No errors in terminal or browser
- [ ] Can have multiple back-and-forth exchanges

---

## Advanced Testing (Optional)

### Test Image Upload (Phase 4 Preview)
1. Click the attachment/upload button in the chat
2. Upload an image (PNG, JPG)
3. Type: `What do you see in this image?`
4. **Expected**: AI analyzes the image and responds

**Note**: This should work already since we built vision support in Phase 1!

---

## Next Steps

Once Phase 1 testing works:
- ✅ You're ready for **Phase 2: Voice Input**
- We'll add speech-to-text so you can speak instead of type

---

## Getting Help

If something doesn't work:
1. Check the terminal output for error messages
2. Check browser console (F12 → Console tab) for errors
3. Verify your API key is correct
4. Make sure all dependencies installed correctly

**Ready to test? Let's go!** 🚀
