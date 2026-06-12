# 🚀 REDDIT API AUTONOMOUS POSTING - SETUP

**Current limitation:** Reddit requires login (can't post without credentials)

## ✅ SOLUTION: Reddit API Credentials (5 minutes to set up)

### Step 1: Create Reddit App
1. Go to: https://www.reddit.com/prefs/apps
2. Scroll to bottom, click "create another app"
3. Fill in:
   - **Name:** I MATCH Financial Advisor Matching
   - **App type:** Select "script"
   - **Description:** AI-powered financial advisor matching platform
   - **About URL:** https://fullpotential.com
   - **Redirect URI:** http://localhost:8080
4. Click "create app"

### Step 2: Save Credentials
You'll get:
- **Client ID:** (under app name, looks like: abc123xyz)
- **Client Secret:** (shown in the app details)

### Step 3: Add to Credential Vault
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./session-set-credential.sh reddit_client_id "YOUR_CLIENT_ID" api_key reddit
./session-set-credential.sh reddit_client_secret "YOUR_SECRET" api_key reddit
./session-set-credential.sh reddit_username "YOUR_REDDIT_USERNAME" username reddit
./session-set-credential.sh reddit_password "YOUR_REDDIT_PASSWORD" password reddit
```

### Step 4: Autonomous Posting Activated
Once credentials are set, run:
```bash
python3 /Users/jamessunheart/Development/agents/services/i-match/reddit_autonomous_post.py
```

**Result:** Posts to Reddit autonomously, no browser needed!

---

## 🎯 ALTERNATIVE: Manual Post Now (2 minutes)

Safari is already open at the submit page. Just:
1. Log in to Reddit
2. Paste title + content (from terminal output above)
3. Click "Post"

**Then we can set up API for future autonomous posting.**

---

**Which path do you want?**
- A) Set up Reddit API now (5 min, fully autonomous forever)
- B) Manual post now (2 min, quick win)
