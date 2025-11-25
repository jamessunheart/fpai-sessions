#!/bin/bash
# Start the feedback service
cd /Users/jamessunheart/FPAI_Cockpit/SERVICES/apprentice-feedback
nohup python3 app.py > feedback.log 2>&1 &
echo "Feedback service started on port 8055"
