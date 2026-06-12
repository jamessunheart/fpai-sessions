# Quick Commands Reference

## Navigate to Project Folder

```powershell
cd C:\Users\Zaibtech.pk\.cursor\voice-interface
```

## Verify Setup

```powershell
python quick_test.py
```

## Create .env File

```powershell
# Create file
New-Item -Path ".env" -ItemType File -Force

# Open in Notepad
notepad .env
```

**Then add this line to the file:**
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Install Dependencies

```powershell
pip install -r requirements.txt
```

## Start the App

```powershell
chainlit run app.py -w
```

## Full Setup Sequence

```powershell
# 1. Navigate to folder
cd C:\Users\Zaibtech.pk\.cursor\voice-interface

# 2. Install dependencies (if not done)
pip install -r requirements.txt

# 3. Create .env file
New-Item -Path ".env" -ItemType File -Force
notepad .env
# (Add API key in Notepad, save and close)

# 4. Verify setup
python quick_test.py

# 5. Start app
chainlit run app.py -w

# 6. Open browser to: http://localhost:8000
```

## Check Current Directory

```powershell
# See where you are
pwd

# See files in current directory
dir

# You should see: app.py, config.py, requirements.txt, etc.
```
