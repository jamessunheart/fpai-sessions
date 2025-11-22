@echo off
echo Testing heartbeat endpoint...
curl -X GET http://localhost:3000/api/test-heartbeat
echo.
echo.
echo Done!
pause
