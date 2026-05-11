@echo off
echo Testing Registry v2 API Integration...
echo.

echo Step 1: Get JWT Token
curl -X POST "https://drop18.fullpotential.ai/auth/token?droplet_id=drop5.fullpotential.ai" -H "X-Registry-Key: a5447df6e4fe34df8c4d0c671ad98ce78de9e55cf152e5d07e5bf221769e31dc"
echo.
echo.

echo Step 2: Get All Droplets (via proxy)
curl -s "http://localhost:3000/api/proxy?endpoint=/registry/droplets"
echo.
echo.

echo Done!
