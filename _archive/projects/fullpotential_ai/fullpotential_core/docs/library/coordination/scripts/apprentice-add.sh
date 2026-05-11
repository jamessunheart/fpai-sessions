#!/bin/bash
# Add new apprentice to tracking system

if [ $# -lt 3 ]; then
    echo "Usage: ./apprentice-add.sh <apprentice_id> <name> <upwork_url>"
    echo "Example: ./apprentice-add.sh upwork_jane_smith \"Jane Smith\" \"https://upwork.com/freelancers/~...\""
    exit 1
fi

APPRENTICE_ID=$1
NAME=$2
UPWORK_URL=$3
TRACKING_FILE="../APPRENTICE_TRACKING.json"

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "Adding apprentice: $NAME ($APPRENTICE_ID)"

# Create entry (manual for now - can automate with jq later)
echo ""
echo "Add this to APPRENTICE_TRACKING.json under 'apprentices':"
echo ""
cat << EOF
  "$APPRENTICE_ID": {
    "apprentice_id": "$APPRENTICE_ID",
    "name": "$NAME",
    "upwork_profile": "$UPWORK_URL",
    "email": "TBD",
    "tier": "starter",
    "tasks_completed": 0,
    "tasks_active": [],
    "total_earned": "\$0",
    "bonuses_earned": "\$0",
    "joined_at": "$TIMESTAMP",
    "last_active": "$TIMESTAMP",
    "skills": [],
    "performance_rating": 0,
    "notes": "New apprentice - first tasks pending"
  }
EOF

echo ""
echo "✅ Entry template created. Copy to $TRACKING_FILE"
