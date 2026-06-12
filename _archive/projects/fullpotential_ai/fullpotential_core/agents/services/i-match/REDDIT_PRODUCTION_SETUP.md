# 🚀 REDDIT AUTONOMOUS POSTING - PRODUCTION SETUP

## CORRECT PRODUCTION CONFIGURATION

**Use REAL domain:** https://fullpotential.com

### Reddit App Setup (2 minutes):

1. **Go to:** https://www.reddit.com/prefs/apps
2. **Click:** "create another app"
3. **Fill in:**
   - **Name:** I-MATCH-Financial-Advisor-Bot
   - **App type:** web app
   - **Description:** AI-powered financial advisor matching platform
   - **About URL:** https://fullpotential.com
   - **Redirect URI:** https://fullpotential.com/api/reddit/callback
4. **Click:** "create app"

### Production Benefits:
✅ Real domain (not localhost)
✅ Works from anywhere (not just local)
✅ Professional (fullpotential.com, not 127.0.0.1)
✅ Can handle OAuth callbacks on server
✅ Scalable to multiple bots

### Credentials Needed:
- Client ID (shown under app name)
- Client Secret (shown in app)
- Your Reddit username
- Your Reddit password

### Save to Production:
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./session-set-credential.sh reddit_client_id "YOUR_ID" api_key reddit
./session-set-credential.sh reddit_client_secret "YOUR_SECRET" api_key reddit
./session-set-credential.sh reddit_username "YOUR_USERNAME" username reddit
./session-set-credential.sh reddit_password "YOUR_PASSWORD" password reddit
```

### Deploy Callback Handler to Server:
```bash
# This creates the /api/reddit/callback endpoint on production
ssh root@198.54.123.234 "cat > /root/reddit_callback.py" << 'CALLBACK'
from fastapi import FastAPI, Request
app = FastAPI()

@app.get("/api/reddit/callback")
async def reddit_callback(code: str, state: str):
    # OAuth callback - Reddit will hit this after auth
    return {"status": "authorized", "code": code}
CALLBACK
```

### Then Post Autonomously:
```python
python3 reddit_autonomous_post.py
# Posts immediately, no browser needed!
```

---

**This is the REAL production way to do it.** 🚀
