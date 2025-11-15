#!/bin/bash
# Save Session - Run at end of every session to preserve history

set -e

cd ~/Development

echo "💾 Saving session to collective memory..."
echo ""

# Check if git repo exists
if [ ! -d ".git" ]; then
    echo "❌ Git repository not initialized!"
    echo "   Run: bash ~/Development/setup-sessions-repo.sh"
    exit 1
fi

# Get session number from user
echo "📝 Enter session number (check AUTONOMOUS_BUILD_LOG.md for latest):"
read -p "Session #: " SESSION_NUM

# Get brief description
echo ""
echo "📋 Enter brief session objective (e.g., 'Webhook Deployment System'):"
read -p "Objective: " SESSION_OBJ

# Add all changes
echo ""
echo "1️⃣ Staging session files..."
git add SESSIONS/

# Show what's being committed
echo ""
echo "2️⃣ Files to be committed:"
git status --short

# Create commit
echo ""
echo "3️⃣ Creating commit..."
git commit -m "Session $SESSION_NUM: $SESSION_OBJ

$(tail -20 ~/Development/SESSIONS/AUTONOMOUS_BUILD_LOG.md | grep -A 10 "Session $SESSION_NUM" | head -15)

🌐⚡💎 Session $SESSION_NUM Complete - One Evolving Mind"

# Push to GitHub
echo ""
echo "4️⃣ Pushing to GitHub..."
git push

echo ""
echo "✅ Session $SESSION_NUM saved to collective memory!"
echo ""
echo "📍 Session history preserved at:"
echo "   https://github.com/jamessunheart/fpai-sessions"
echo ""
echo "🧠 Future sessions will learn from this one."
echo ""
