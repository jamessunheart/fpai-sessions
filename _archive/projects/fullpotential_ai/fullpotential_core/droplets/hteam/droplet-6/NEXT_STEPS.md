# Next Steps After Installation

## ✅ Installation Complete!

Once you see `Successfully installed` messages, you're ready to proceed.

---

## Step 1: Create `.env` File

Create a file named `.env` in the `voice-interface` folder:

**Option A: Using PowerShell**
```powershell
# Create the file
New-Item -Path ".env" -ItemType File

# Edit it (will open in Notepad)
notepad .env
```

**Option B: Using Notepad directly**
1. Open Notepad
2. Type: `ANTHROPIC_API_KEY=sk-ant-your-key-here`
3. Save as `.env` (make sure to select "All Files" in the save dialog)
4. Save it in the `voice-interface` folder

**The `.env` file should contain:**
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Important**: Replace `sk-ant-your-actual-key-here` with your real Anthropic API key (get it from James).

---

## Step 2: Verify Setup (Optional)

Run the quick test script to verify everything is ready:

```powershell
python quick_test.py
```

This checks:
- ✅ All dependencies installed
- ✅ `.env` file exists
- ✅ API key is set correctly

---

## Step 3: Start the Application

Run:

```powershell
chainlit run app.py -w
```

The `-w` flag enables auto-reload (server restarts when you change code).

**Expected output:**
```
╭─────────────────────────────────────────────────────────╮
│                                                          │
│  Chainlit                                                │
│                                                          │
│  Your app is running at http://localhost:8000           │
│                                                          │
╰─────────────────────────────────────────────────────────╯
```

---

## Step 4: Open in Browser

1. Open your web browser (Chrome, Edge, or Firefox)
2. Go to: `http://localhost:8000`
3. You should see the chat interface!

---

## Step 5: Test It

Try these messages:
1. `Hello, what can you help me with?`
2. `What's blocking TIER 1 today?`
3. `Can you elaborate on that?` (should remember previous message)

---

## Troubleshooting

### If you get "ANTHROPIC_API_KEY not found":
- Make sure `.env` file exists in the `voice-interface` folder
- Check the file has exactly: `ANTHROPIC_API_KEY=sk-ant-...`
- No quotes around the key
- Restart the server after creating `.env`

### If you get "Module not found":
- Make sure installation completed successfully
- Try: `pip install chainlit anthropic python-dotenv` again

### If port 8000 is busy:
```powershell
chainlit run app.py -w --port 8001
```
Then open `http://localhost:8001`

---

## What to Expect

✅ **Working correctly if**:
- You get responses within 2-5 seconds
- Responses are short (1-3 sentences)
- AI remembers previous messages
- No error messages

❌ **Not working if**:
- You see "Error: API key invalid"
- Responses take more than 10 seconds
- Python traceback errors appear

---

**Ready? Let's go!** 🚀
