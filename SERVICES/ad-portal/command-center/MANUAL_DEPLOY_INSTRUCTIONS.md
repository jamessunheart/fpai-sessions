# Manual Deploy: Ad Portal Command Center

**Goal:** Deploy to `https://fullpotential.ai/projects/advertising`

---

## Step 1: Upload Files to Server

**From James's Mac** (or wherever the repo is), run:

```bash
# First, create the directory on the server
ssh root@198.54.123.234 "mkdir -p /opt/fpai/core/applications/website-ai/frontend/projects/advertising"

# Then upload the files
scp /Users/jamessunheart/FPAI_Cockpit/SERVICES/ad-portal/command-center/index.html \
    /Users/jamessunheart/FPAI_Cockpit/SERVICES/ad-portal/command-center/tasks.json \
    root@198.54.123.234:/opt/fpai/core/applications/website-ai/frontend/projects/advertising/
```

---

## Step 2: Create Projects Hub (On Server)

SSH into the server and run:

```bash
ssh root@198.54.123.234
```

Then on the server:

```bash
mkdir -p /opt/fpai/core/applications/website-ai/frontend/projects

cat > /opt/fpai/core/applications/website-ai/frontend/projects/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Potential AI - Projects</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: system-ui, sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); }
    </style>
</head>
<body class="gradient-bg min-h-screen text-white">
    <div class="max-w-4xl mx-auto p-8">
        <h1 class="text-4xl font-bold mb-8">🚀 Active Projects</h1>
        <div class="space-y-4">
            <a href="/projects/advertising" class="block bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:bg-slate-800 transition">
                <h2 class="text-xl font-semibold text-emerald-400">📡 Ad Portal</h2>
                <p class="text-slate-400 mt-2">Advertising campaign management for coaching offers. Track ROAS to profits.</p>
                <p class="text-sm text-slate-500 mt-2">Status: Setup & Deployment Phase</p>
            </a>
        </div>
        <p class="text-slate-500 text-sm mt-8">Full Potential AI Project Hub</p>
    </div>
</body>
</html>
EOF
```

---

## Step 3: Add Nginx Location (On Server)

Edit the nginx config to serve the static files:

```bash
nano /etc/nginx/sites-available/fullpotential.ai
```

Add this location block **BEFORE** the main `location /` block:

```nginx
    # ====================================================
    # 📁 PROJECTS DIRECTORY (Static Files)
    # ====================================================
    location /projects/ {
        alias /opt/fpai/core/applications/website-ai/frontend/projects/;
        index index.html;
        try_files $uri $uri/ $uri/index.html =404;
    }
```

Then reload nginx:

```bash
nginx -t && systemctl reload nginx
```

---

## Step 4: Verify

```bash
curl -I https://fullpotential.ai/projects/advertising/
# Should return: HTTP/2 200
```

---

## Done!

Access at: **https://fullpotential.ai/projects/advertising**

The command center shows all tasks with step-by-step instructions for the Ad Portal deployment.


