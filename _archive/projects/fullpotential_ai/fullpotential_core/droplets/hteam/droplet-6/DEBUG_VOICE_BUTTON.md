# Debug Voice Button - Step by Step

## 🔍 Step 1: Check Browser Console

1. **Open Browser Console**:
   - Press `F12` (or `Ctrl+Shift+I` on Windows)
   - Click on "Console" tab

2. **Look for these messages**:
   - ✅ "Attempting to add voice button..." (should appear multiple times)
   - ✅ "Voice input button added successfully" (should appear once)
   - ❌ Any **red error messages**

3. **What to report**:
   - Do you see "Attempting to add voice button..." messages?
   - Do you see "Voice input button added successfully"?
   - Any red error messages?

---

## 🔍 Step 2: Check if head.html is Loading

1. **Open Browser DevTools**:
   - Press `F12`
   - Click on "Elements" or "Inspector" tab

2. **Check the `<head>` section**:
   - Look for `<style>` tags with `.voice-input-btn` class
   - Look for `<script>` tags with voice input code

3. **If you see the styles/scripts**:
   - ✅ head.html is loading correctly
   - The issue is with finding the input element

4. **If you DON'T see the styles/scripts**:
   - ❌ head.html is not loading
   - Need to check Chainlit configuration

---

## 🔍 Step 3: Check if Input Element Exists

1. **In Console tab**, type this command:
   ```javascript
   document.querySelector('textarea, input[type="text"]')
   ```

2. **What it should return**:
   - If it returns an element: ✅ Input found
   - If it returns `null`: ❌ Input not found

3. **Try this command too**:
   ```javascript
   document.querySelector('textarea[placeholder*="message"]')
   ```

4. **Check the container**:
   ```javascript
   const input = document.querySelector('textarea, input[type="text"]');
   input ? input.closest('form') : null
   ```

---

## 🔍 Step 4: Manual Button Test

1. **In Console tab**, run this command to manually add the button:
   ```javascript
   const input = document.querySelector('textarea, input[type="text"]');
   if (input) {
       const container = input.closest('form') || input.parentElement;
       const btn = document.createElement('button');
       btn.id = 'voice-input-btn';
       btn.type = 'button';
       btn.className = 'voice-input-btn';
       btn.innerHTML = '🎤';
       btn.style.cssText = 'position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: #4CAF50; color: white; border: none; border-radius: 50%; width: 48px; height: 48px; cursor: pointer; z-index: 1000;';
       container.style.position = 'relative';
       container.appendChild(btn);
       console.log('Button added manually');
   } else {
       console.log('Input not found');
   }
   ```

2. **Does the button appear?**
   - ✅ Yes: Script is working, just timing issue
   - ❌ No: Input element not found or container issue

---

## 🐛 Common Issues

### Issue 1: head.html Not Loading
**Symptoms**: No styles/scripts in `<head>`

**Fix**: Check if `.chainlit/head.html` exists and restart app

### Issue 2: Input Element Not Found
**Symptoms**: Console shows "Attempting..." but no success

**Fix**: Chainlit might use different selectors. Need to update findInput() function

### Issue 3: Timing Issue
**Symptoms**: Button appears after page interaction

**Fix**: Delay is too short, or Chainlit loads input dynamically

### Issue 4: Container Positioning
**Symptoms**: Button appears but in wrong position

**Fix**: Container might not have `position: relative`

---

## 📝 Quick Checklist

- [ ] Open browser console (F12)
- [ ] Check for "Attempting to add voice button..." messages
- [ ] Check for "Voice input button added successfully" message
- [ ] Check for any red error messages
- [ ] Check if head.html is loading (Elements tab → head section)
- [ ] Test manual button creation (copy command above)
- [ ] Report findings

---

**Run these checks and report back what you find!** 🚀
