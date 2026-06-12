@echo off
REM UDC API Test Script for Droplet #5 (Dashboard) - Windows Version

if "%DASHBOARD_URL%"=="" (
    set ENDPOINT=http://localhost:3000
) else (
    set ENDPOINT=%DASHBOARD_URL%
)

echo Testing UDC API Endpoints for Droplet #5
echo Endpoint: %ENDPOINT%
echo ==========================================

echo.
echo 1. GET /health
curl -X GET "%ENDPOINT%/api/health" -H "Accept: application/json" -w "\nStatus: %%{http_code}\n"

echo.
echo 2. GET /capabilities
curl -X GET "%ENDPOINT%/api/capabilities" -H "Accept: application/json" -w "\nStatus: %%{http_code}\n"

echo.
echo 3. GET /state
curl -X GET "%ENDPOINT%/api/state" -H "Accept: application/json" -w "\nStatus: %%{http_code}\n"

echo.
echo 4. GET /dependencies
curl -X GET "%ENDPOINT%/api/dependencies" -H "Accept: application/json" -w "\nStatus: %%{http_code}\n"

echo.
echo 5. GET /version
curl -X GET "%ENDPOINT%/api/version" -H "Accept: application/json" -w "\nStatus: %%{http_code}\n"

echo.
echo 6. POST /message
curl -X POST "%ENDPOINT%/api/message" -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"source\":\"droplet-10\",\"target\":\"droplet-5\",\"message_type\":\"command\",\"payload\":{\"command\":\"test\",\"data\":\"Hello from test script\"},\"timestamp\":\"%date:~-4%-%date:~4,2%-%date:~7,2%T%time:~0,2%:%time:~3,2%:%time:~6,2%Z\",\"trace_id\":\"test-trace-%random%\"}" -w "\nStatus: %%{http_code}\n"

echo.
echo 7. POST /send
curl -X POST "%ENDPOINT%/api/send" -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"target_droplet_id\":\"droplet-10\",\"message_type\":\"query\",\"payload\":{\"query\":\"status\"}}" -w "\nStatus: %%{http_code}\n"

echo.
echo 8. POST /reload-config
curl -X POST "%ENDPOINT%/api/reload-config" -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"reason\":\"Test reload from script\"}" -w "\nStatus: %%{http_code}\n"

echo.
echo ==========================================
echo UDC API Test Complete
