# 🚀 Apprentice Submission & Feedback Portal

**Status:** Ready for Deployment
**Service:** Apprentice Feedback
**Port:** 8055

## Overview
The Apprentice Feedback System has been upgraded to support **Automated Code Harvesting**.

## 🔗 How to Submit
Apprentices can now visit the feedback portal (default: `http://localhost:8055`) to submit their work.

1. **Status:** Select **"📤 Submitting Code"**
2. **Repo URL:** Enter GitHub repository link (e.g., `https://github.com/user/repo`)
3. **Submit:** The system automatically triggers the Harvester.

## ⚙️ Technical Details

- **Service Location:** `SERVICES/apprentice-feedback/app.py`
- **Auto-Harvest:** Triggers `_scripts/harvest-apprentice.py` in background
- **Logs:** `data/apprentice-feedback/all_feedback.jsonl`

## 🛠️ Deployment
To start the service in production (or outside sandbox):

```bash
cd SERVICES/apprentice-feedback
./start.sh
```

*Note: In the current sandbox environment, port binding may be restricted. Deploy to a live server or local machine with appropriate permissions.*
