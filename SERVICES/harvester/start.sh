#!/bin/bash
# Start the harvester service
cd /root/FPAI_Cockpit/SERVICES/harvester
nohup python3 app.py > feedback.log 2>&1 &
echo "Harvester service started on port 8055"
