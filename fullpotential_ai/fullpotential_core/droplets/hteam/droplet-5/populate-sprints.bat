@echo off
echo Creating sprint records...

curl -X POST "https://drop2.fullpotential.ai/sprints" -H "Content-Type: application/json" -d "{\"Sprint_ID\":\"SP-001\",\"Name\":\"Dashboard UI Enhancement\",\"Dev_Name\":\"Haythem\",\"Status\":\"Active\",\"Time_Spent_hr\":5,\"Notes\":\"Working on sprint management\"}"

curl -X POST "https://drop2.fullpotential.ai/sprints" -H "Content-Type: application/json" -d "{\"Sprint_ID\":\"SP-002\",\"Name\":\"API Integration\",\"Dev_Name\":\"Haythem\",\"Status\":\"Done\",\"Time_Spent_hr\":8,\"Notes\":\"Completed API endpoints\"}"

curl -X POST "https://drop2.fullpotential.ai/sprints" -H "Content-Type: application/json" -d "{\"Sprint_ID\":\"SP-003\",\"Name\":\"UDC Compliance\",\"Dev_Name\":\"Haythem\",\"Status\":\"Done\",\"Time_Spent_hr\":3,\"Notes\":\"All endpoints verified\"}"

curl -X POST "https://drop2.fullpotential.ai/sprints" -H "Content-Type: application/json" -d "{\"Sprint_ID\":\"SP-004\",\"Name\":\"Authentication System\",\"Dev_Name\":\"Haythem\",\"Status\":\"Pending\",\"Time_Spent_hr\":0,\"Notes\":\"Planned for next week\"}"

curl -X POST "https://drop2.fullpotential.ai/sprints" -H "Content-Type: application/json" -d "{\"Sprint_ID\":\"SP-005\",\"Name\":\"Real-time Monitoring\",\"Dev_Name\":\"Haythem\",\"Status\":\"Active\",\"Time_Spent_hr\":6,\"Notes\":\"Implementing live updates\"}"

echo.
echo Sprint records created successfully!
echo.
echo Testing sprints endpoint...
curl -s "https://drop2.fullpotential.ai/sprints"
