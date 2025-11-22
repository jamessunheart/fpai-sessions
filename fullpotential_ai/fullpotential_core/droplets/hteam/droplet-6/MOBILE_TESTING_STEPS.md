# Step 4: Mobile Testing - Complete Guide

## 📱 Testing on Mobile Device

### Step 1: Navigate to Project Folder

```powershell
cd C:\Users\Zaibtech.pk\.cursor\voice-interface
```

### Step 2: Find Your IP Address

Run this command:

```powershell
python get_ip_address.py
```

**Expected output**:
```
==================================================
Your IP Address for Mobile Testing:
==================================================

IP Address: 192.168.1.XXX

Access from phone (same WiFi):
http://192.168.1.XXX:8000

==================================================
```

**Note your IP address** (you'll need it for Step 4)

---

### Step 3: Start Chainlit with External Access

**IMPORTANT**: You need to use `--host 0.0.0.0` to allow external connections.

```powershell
chainlit run app.py -w --host 0.0.0.0
```

**What this does**:
- `-w` = Auto-reload on file changes
- `--host 0.0.0.0` = Allows connections from other devices on your network

**Expected output**:
```
╭─────────────────────────────────────────────────────────╭
│  Your app is running at http://0.0.0.0:8000             │
│  Also accessible at http://YOUR_IP:8000                 │
╰─────────────────────────────────────────────────────────╯
```

**Keep this terminal window open** - don't close it!

---

### Step 4: Access from Mobile Device

**Requirements**:
- ✅ Your phone must be on the **same WiFi network** as your computer
- ✅ Both devices on same network (not mobile data)

**Steps**:

1. **On your phone**, open a web browser (Chrome, Safari, etc.)

2. **Type the URL**:
   ```
   http://YOUR_IP:8000
   ```
   Replace `YOUR_IP` with the IP address from Step 2
   
   **Example**:
   ```
   http://192.168.1.100:8000
   ```

3. **Press Enter/Go**

4. **You should see**: The chat interface on your phone!

---

### Step 5: Test on Mobile

**Test these features**:

1. **Basic Chat**:
   - Type a message
   - Send it
   - Verify response appears

2. **Conversation Memory**:
   - Ask a question
   - Ask a follow-up
   - Verify AI remembers context

3. **Image Upload** (if available):
   - Click attachment button
   - Upload an image
   - Type: "What do you see?"
   - Verify AI analyzes image

4. **Mobile UI**:
   - Check if interface is usable
   - Check if text input works
   - Check if buttons are clickable

---

## 🔧 Troubleshooting

### Problem: Can't connect from phone

**Solutions**:

1. **Check firewall**:
   - Windows might block the connection
   - You may need to allow port 8000 in firewall
   - Or temporarily disable firewall for testing

2. **Check IP address**:
   - Make sure you're using the correct IP
   - Run `python get_ip_address.py` again to verify

3. **Check network**:
   - Both devices must be on same WiFi
   - Not mobile data on phone
   - Not different networks

4. **Try different port**:
   ```powershell
   chainlit run app.py -w --host 0.0.0.0 --port 8001
   ```
   Then use: `http://YOUR_IP:8001`

### Problem: Firewall blocking connection

**Windows Firewall Solution**:

1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Add Python or allow port 8000

**Quick PowerShell fix** (run as Administrator):
```powershell
New-NetFirewallRule -DisplayName "Chainlit" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Problem: IP address not found

**Alternative method to find IP**:

**Windows**:
```powershell
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter (usually `192.168.x.x`)

**Or use this command**:
```powershell
ipconfig | findstr IPv4
```

---

## ✅ Success Indicators

**Working correctly if**:
- ✅ App loads on mobile browser
- ✅ Chat interface appears
- ✅ Can type messages
- ✅ Can send messages
- ✅ Responses appear
- ✅ Interface is usable on mobile

**Not working if**:
- ❌ "Connection refused" error
- ❌ "Cannot reach site" error
- ❌ Blank page
- ❌ Timeout errors

---

## 📝 Quick Reference

**All commands in sequence**:

```powershell
# 1. Navigate to folder
cd C:\Users\Zaibtech.pk\.cursor\voice-interface

# 2. Find IP address
python get_ip_address.py

# 3. Start Chainlit with external access
chainlit run app.py -w --host 0.0.0.0

# 4. On phone: Open http://YOUR_IP:8000
```

---

**Ready to test on mobile?** Follow these steps! 🚀
