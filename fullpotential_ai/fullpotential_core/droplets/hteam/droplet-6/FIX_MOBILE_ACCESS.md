# Fix Mobile Access - Quick Guide

## 🔧 The Problem

`0.0.0.0` is NOT a valid address to browse to. It's a special address that means "listen on all interfaces" but you can't actually browse to it.

## ✅ The Solution

### For Laptop (Local Access):
Use: `http://localhost:8000` or `http://127.0.0.1:8000`

### For Phone (Mobile Access):
Use: `http://192.168.18.45:8000` (your actual IP address)

---

## 📝 Step-by-Step Fix

### Step 1: Keep Chainlit Running

Chainlit is already running correctly with `--host 0.0.0.0`. This is correct - **don't stop it!**

```
chainlit run app.py -w --host 0.0.0.0
```

### Step 2: Access on Laptop

**Open in browser:**
```
http://localhost:8000
```

**OR:**

```
http://127.0.0.1:8000
```

**NOT** `http://0.0.0.0:8000` (this won't work!)

### Step 3: Access on Phone

**On your phone (same WiFi), open:**
```
http://192.168.18.45:8000
```

**This is your actual IP address from the script!**

---

## 🔍 If Phone Still Can't Connect

### Check 1: Firewall

Windows Firewall might be blocking the connection. Try allowing port 8000:

**Option A: PowerShell (Run as Administrator)**
```powershell
New-NetFirewallRule -DisplayName "Chainlit Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

**Option B: Windows Firewall Settings**
1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Click "Allow another app"
4. Add Python or allow port 8000

### Check 2: Same WiFi Network

Make sure:
- ✅ Phone is on the **same WiFi network** as your laptop
- ✅ Not using mobile data on phone
- ✅ Both devices on same network

### Check 3: Try Different Port

If port 8000 is blocked, try port 8001:

**Stop Chainlit** (Ctrl+C), then:
```powershell
chainlit run app.py -w --host 0.0.0.0 --port 8001
```

Then on phone use: `http://192.168.18.45:8001`

---

## ✅ Quick Reference

**Laptop Access:**
- ✅ `http://localhost:8000`
- ✅ `http://127.0.0.1:8000`
- ❌ `http://0.0.0.0:8000` (doesn't work!)

**Phone Access:**
- ✅ `http://192.168.18.45:8000`
- ❌ `http://0.0.0.0:8000` (doesn't work!)

---

**Try these now and let me know if it works!** 🚀
