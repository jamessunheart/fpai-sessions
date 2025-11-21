#!/bin/bash
# Quick update script for LAUNCH_TRACKER.md
echo "Enter providers recruited (0-20): "
read providers
echo "Enter customers acquired (0-20): "
read customers
echo "Enter matches generated (0-60): "
read matches
echo "Enter engagements confirmed (0-10): "
read engagements
echo "Enter revenue invoiced (\$): "
read revenue

# Update the tracker
sed -i.bak "s/Providers Recruited:** [0-9]*/Providers Recruited:** $providers/" ../LAUNCH_TRACKER.md
sed -i.bak "s/Customers Acquired:** [0-9]*/Customers Acquired:** $customers/" ../LAUNCH_TRACKER.md
sed -i.bak "s/Matches Generated:** [0-9]*/Matches Generated:** $matches/" ../LAUNCH_TRACKER.md
sed -i.bak "s/Engagements Confirmed:** [0-9]*/Engagements Confirmed:** $engagements/" ../LAUNCH_TRACKER.md
sed -i.bak "s/Revenue Invoiced:** \\\$[0-9,]*/Revenue Invoiced:** \$$revenue/" ../LAUNCH_TRACKER.md
sed -i.bak "s/Last Updated:**.*/Last Updated:** $(date)/" ../LAUNCH_TRACKER.md

echo "✅ Tracker updated!"
cat ../LAUNCH_TRACKER.md
