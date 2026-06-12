# Troubleshoot Voice Button Not Showing

## 🔍 Step 1: Check Browser Console

**Open Browser Console:**
1. Press `F12` (or `Ctrl+Shift+I`)
2. Go to "Console" tab
3. Look for messages starting with `[Voice Input]`

**What to look for:**
- `[Voice Input] Script loaded successfully` - Means JS file is loading
- `[Voice Input] Speech API supported: true/false` - Browser support
- `[Voice Input] Attempting to add voice button...` - Script is trying
- `[Voice Input] Input element found: YES/NO` - If input is found
- `[Voice Input] Voice input button added successfully` - Success!

**Report what you see!**

---

## 🔍 Step 2: Check if Files Are Loading

**In Browser DevTools:**
1. Press `F12`
2. Go to "Network" tab
3. Refresh page (`Ctrl+R`)
4. Look for:
   - `voice_input.css` - Should load with status 200
   - `voice_input.js` - Should load with status 200

**If files show 404:**
- Files aren't in the right location
- Need to check public directory

---

## 🔍 Step 3: Check Config File

**Verify config.toml has:**
```toml
custom_css = "/public/voice_input.css"
custom_js = "/public/voice_input.js"
```

**Location:** `.chainlit/config.toml`

---

## 🔍 Step 4: Manual Test

**In Console tab, run this:**
```javascript
// Check if input exists
const input = document.querySelector('textarea, input[type="text"], [contenteditable="true"]');
console.log('Input found:', input ? 'YES' : 'NO');
if (input) {
    console.log('Input:', input);
    console.log('Container:', input.closest('form') || input.parentElement);
}

// Check if button already exists
console.log('Button exists:', document.getElementById('voice-input-btn') ? 'YES' : 'NO');
```

**Report what it shows!**

---

## 🔍 Step 5: Manual Button Creation

**In Console, run this to manually create button:**
```javascript
const input = document.querySelector('textarea, input[type="text"], [contenteditable="true"]');
if (input) {
    const container = input.closest('form') || input.parentElement;
    const btn = document.createElement('button');
    btn.id = 'voice-input-btn';
    btn.type = 'button';
    btn.innerHTML = '🎤';
    btn.style.cssText = 'position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: #4CAF50; color: white; border: none; border-radius: 50%; width: 48px; height: 48px; cursor: pointer; z-index: 1000;';
    container.style.position = 'relative';
    container.appendChild(btn);
    console.log('Button added manually!');
} else {
    console.log('Input not found!');
}
```

**Does the button appear?**
- ✅ Yes: Script works, just timing issue
- ❌ No: Input element not found or container issue

---

## 🐛 Common Issues

### Issue 1: Files Not Loading (404)
**Fix:** 
- Check `public/` directory exists
- Check files are named correctly
- Restart Chainlit server

### Issue 2: Config Not Applied
**Fix:**
- Check `.chainlit/config.toml` has correct paths
- Restart Chainlit server
- Clear browser cache

### Issue 3: Input Element Not Found
**Fix:**
- Chainlit might use different selectors
- Need to update `findInput()` function
- Check console for input element

### Issue 4: Timing Issue
**Fix:**
- Chainlit loads input dynamically
- Script might run too early
- Already added multiple retries

---

## 📝 What to Report

Please share:
1. **Console messages** - What do you see with `[Voice Input]` prefix?
2. **Network tab** - Do `voice_input.css` and `voice_input.js` load?
3. **Manual test results** - What does the manual button creation show?

This will help identify the exact issue!
