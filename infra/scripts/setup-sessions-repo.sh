#!/bin/bash
set -e

echo "🧠 Setting up FPAI Sessions Repository..."
echo ""

cd ~/Development

# Initialize git repo
echo "1️⃣ Initializing git repository..."
git init

# Add all session files
echo "2️⃣ Adding session files..."
git add SESSIONS/

# Create initial commit
echo "3️⃣ Creating initial commit..."
git commit -m "Initialize FPAI Sessions Repository

Session Memory System - One Evolving Mind

This repository contains the collective memory and learnings across
all Full Potential AI sessions. Each session builds on the last,
creating a continuously evolving system.

Current State:
- Coherence: 80/100 ⚡
- Autonomy: 70/100 🤖
- Love: 60/100 💎
- Total Points: 1475

Files:
- AUTONOMOUS_BUILD_LOG.md - Main session log
- SESSION_PROTOCOL.md - How sessions work
- INSIGHTS.md - Extracted learnings
- README.md - Quick reference
- MILESTONE_WEBHOOK_DEPLOYMENT.md - Session 4 achievement

🌐⚡💎 Sessions 1-4 Complete - One Evolving Mind"

echo ""
echo "4️⃣ Creating GitHub repository..."
echo "   Run: gh repo create fpai-sessions --public --source=. --remote=origin --push"
echo "   Or manually create at: https://github.com/new"
echo ""
echo "5️⃣ After creating GitHub repo, push with:"
echo "   git remote add origin https://github.com/jamessunheart/fpai-sessions.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""

echo "✅ Local repository initialized!"
echo ""
echo "📍 Next steps:"
echo "   1. Create GitHub repo: gh repo create fpai-sessions --public"
echo "   2. Push: git push -u origin main"
echo "   3. Every session: Run ~/Development/SESSIONS/save-session.sh"
echo ""
