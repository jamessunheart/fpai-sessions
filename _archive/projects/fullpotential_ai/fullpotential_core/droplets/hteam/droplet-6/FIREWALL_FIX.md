# Firewall Configuration - Step by Step

## 🔧 Fix Windows Firewall for Chainlit

### Method 1: PowerShell (Fastest - Run as Administrator)

**Step 1: Open PowerShell as Administrator**
1. Press `Windows + X`
2. Click "Windows PowerShell (Admin)" or "Terminal (Admin)"
3. Click "Yes" when prompted

**Step 2: Allow Port 8000**

Run this command:

```powershell
New-NetFirewallRule -DisplayName "Chainlit Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

**Expected output:**
```
Name                  : Chainlit Port 8000
DisplayName           : Chainlit Port 8000
Description           :
DisplayGroup          :
Group                 :
Enabled               : True
Profile               : Any
Platform              : {}
Direction             : Inbound
Action                : Allow
EdgeTraversalPolicy   : Block
LooseSourceMapping    : False
LocalOnlyMapping      : False
Owner                 :
PrimaryStatus         : OK
Status                : The rule was parsed successfully from the store.
EnforcementStatus     : NotApplicable
PolicyStoreSource     : PersistentStore
PolicyStoreSourceType : Local
```

**Step 3: Verify Rule Created**

Check if rule was created:

```powershell
Get-NetFirewallRule -DisplayName "Chainlit Port 8000"
```

**Step 4: Test Again**

Try accessing from phone again:
```
http://192.168.18.45:8000
```

---

### Method 2: Windows Firewall GUI (Alternative)

**Step 1: Open Windows Defender Firewall**
1. Press `Windows + R`
2. Type: `wf.msc`
3. Press Enter

**Step 2: Create Inbound Rule**
1. Click "Inbound Rules" on the left
2. Click "New Rule..." on the right
3. Select "Port" → Click "Next"
4. Select "TCP"
5. Select "Specific local ports"
6. Enter: `8000`
7. Click "Next"
8. Select "Allow the connection" → Click "Next"
9. Check all profiles (Domain, Private, Public) → Click "Next"
10. Name: `Chainlit Port 8000`
11. Click "Finish"

**Step 3: Test Again**

Try accessing from phone:
```
http://192.168.18.45:8000
```

---

## 🔍 Verify Firewall Configuration

### Check if Port 8000 is Open

Run this command in PowerShell (as Administrator):

```powershell
Get-NetFirewallPortFilter | Where-Object {$_.LocalPort -eq 8000}
```

**Expected output:**
```
Protocol : TCP
LocalPort : 8000
IcmpType  :
DynamicTarget :
EdgeTraversal :
```

---

## 🧪 Test if Firewall is the Issue

### Test 1: Check if Chainlit is Listening

On your laptop, run this command:

```powershell
netstat -an | findstr 8000
```

**Expected output:**
```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING
```

If you see `LISTENING`, Chainlit is running correctly.

### Test 2: Test Local Connection

On your laptop, try:
```
http://localhost:8000
http://127.0.0.1:8000
```

**If these work**: Chainlit is running correctly, issue is likely firewall.

**If these don't work**: Chainlit might not be running correctly.

### Test 3: Test from Phone

On your phone (same WiFi), try:
```
http://192.168.18.45:8000
```

**If this works**: Firewall is fixed!

**If this doesn't work**: Continue troubleshooting below.

---

## 🔧 Alternative Solutions

### Solution 1: Try Different Port

If port 8000 is still blocked, try port 8001:

**Step 1: Stop Chainlit** (Ctrl+C in terminal)

**Step 2: Start with port 8001**
```powershell
chainlit run app.py -w --host 0.0.0.0 --port 8001
```

**Step 3: Allow port 8001 in firewall**
```powershell
New-NetFirewallRule -DisplayName "Chainlit Port 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```

**Step 4: Access from phone**
```
http://192.168.18.45:8001
```

### Solution 2: Temporarily Disable Firewall (Testing Only)

**⚠️ WARNING: Only for testing! Re-enable after testing!**

**Disable firewall temporarily:**
```powershell
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
```

**Test access from phone**

**Re-enable firewall after testing:**
```powershell
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

**Then add proper firewall rule** (Method 1 or 2 above)

---

## 🔍 Additional Troubleshooting

### Check Network Connection

**On laptop:**
```powershell
ipconfig
```

**On phone:**
- Check WiFi settings
- Verify you're on the same network as laptop
- Check IP address (should be similar: `192.168.18.XXX`)

### Check Router Settings

Some routers block local connections:
- Check router firewall settings
- Check if AP isolation is enabled (disable it)
- Check if client isolation is enabled (disable it)

### Test with Different Browser

Try different browsers on phone:
- Chrome
- Safari
- Firefox
- Edge

---

## ✅ Quick Checklist

- [ ] Firewall rule created for port 8000
- [ ] Chainlit running with `--host 0.0.0.0`
- [ ] Phone on same WiFi network
- [ ] Using correct IP address: `192.168.18.45`
- [ ] Using correct port: `8000`
- [ ] Testing with `http://192.168.18.45:8000` (not `http://0.0.0.0:8000`)

---

## 🚀 Quick Fix Commands

**All-in-one PowerShell script (Run as Administrator):**

```powershell
# Allow port 8000
New-NetFirewallRule -DisplayName "Chainlit Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# Verify
Get-NetFirewallRule -DisplayName "Chainlit Port 8000"

# Check if listening
netstat -an | findstr 8000
```

**Then test from phone:**
```
http://192.168.18.45:8000
```

---

**Try the firewall fix first, then test again!** 🚀
