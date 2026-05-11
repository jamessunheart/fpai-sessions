✅ DOCUMENT 1 — Registry v2 Droplet
Integration Guide (UDC-Compliant)
Version: 2.0
Audience: Engineering Teams, Droplet Maintainters
Purpose: Clear instructions for connecting any droplet to the new Registry v2 (Droplet 18)
using JWT authentication + UDC-compliant capabilities.
1. Overview
Registry v2 is the central service that all droplets communicate with for:
● Registration
● Heartbeats
● Capability discovery
● Authentication (JWT)
● UDC compliance validation
Every droplet must complete three steps:
1. Fetch a JWT token (authorized by Registry Key)
2. Register itself with the Registry
3. Send periodic heartbeats with the JWT token
2. Base URL
Production (Droplet 18 Registry v2)
https://drop18.fullpotential.ai
3. Required Endpoints
Purpose Method Endpoint
Health GET /health
Register droplet POST /registry/regis
ter
Heartbeat ping POST /registry/heart
beat
Fetch JWT token POST /auth/token
Fetch public key GET /auth/public_ke
y
UDC schema GET /udc/schema
UDC capabilities GET /udc/capabiliti
es
UDC handshake GET /udc/handshake
4. Authentication
4.1 Registry Key
Every droplet must present the global registry key when asking for a token:
X-Registry-Key: regkey_2f14c9b6e9b047d2b8c5a7cf93b2e4da
4.2 Fetch JWT Token
Request
POST
https://drop18.fullpotential.ai/auth/token?droplet_id={your-droplet-do
main}
Headers:
X-Registry-Key: regkey_2f14c9b6e9b047d2b8c5a7cf93b2e4da
Response
{
"token": "JWT_TOKEN_HERE"
}
4.3 Token Format (Registry v2)
The token uses HS256 with secret stored in the registry.
Claims:
Claim Description
iss Always "registry"
sub Droplet ID (domain)
aud Always "udc"
iat Issued at timestamp
exp Expires in 3600s (1h)
role "droplet"
scop
e
[ "registry:heartbeat",
"registry:register" ]
Example decoded JWT:
{
"iss": "registry",
"sub": "drop5.fullpotential.ai",
"aud": "udc",
"iat": 1763012883,
"exp": 1763016483,
"role": "droplet",
"scope": [
"registry:heartbeat",
"registry:register"
]
}
5. Registration Flow
Endpoint
POST /registry/register
Authorization: Bearer {JWT}
Example Payload
{
"droplet_id": "drop5.fullpotential.ai",
"ip": "24.199.107.120",
"status": "active",
"metadata": {
"version": "1.0.0",
"region": "us-east"
}
}
Response
{"ok": true}
6. Heartbeat Flow
Endpoint
POST /registry/heartbeat
Authorization: Bearer {JWT}
Example payload:
{
"droplet_id": "drop5.fullpotential.ai",
"load": 0.02,
"status": "healthy"
}
Response
{"ok": true, "ts": "2025-11-13T05:21:00Z"}
Heartbeats should be sent every 30 seconds.
7. Example Integration Code
Python Droplet Side
import requests
import time
BASE = "https://drop18.fullpotential.ai"
REGISTRY_KEY = "regkey_2f14c9b6e9b047d2b8c5a7cf93b2e4da"
DROPLET_ID = "drop5.fullpotential.ai"
def get_token():
r = requests.post(
f"{BASE}/auth/token",
params={"droplet_id": DROPLET_ID},
headers={"X-Registry-Key": REGISTRY_KEY}
)
return r.json()["token"]
def register(token):
r = requests.post(
f"{BASE}/registry/register",
json={"droplet_id": DROPLET_ID, "status": "active"},
headers={"Authorization": f"Bearer {token}"}
)
print("registered:", r.text)
def heartbeat(token):
r = requests.post(
f"{BASE}/registry/heartbeat",
json={"droplet_id": DROPLET_ID, "status": "healthy"},
headers={"Authorization": f"Bearer {token}"}
)
print("heartbeat:", r.text)
token = get_token()
register(token)
while True:
heartbeat(token)
time.sleep(30)
8. UDC Compliance Endpoints
/udc/schema
Shows all registry-provided capabilities.
/udc/capabilities
Confirms the droplet meets UDC requirements.
/udc/handshake
Used by external systems for initial protocol confirmation.
9. Error Codes
Code Meaning
401 Invalid token or invalid registry key
403 Token scope missing
422 Droplet ID missing or invalid
500 Internal registry error
10. Checklist for Droplet Teams
● Can fetch token
● Can register
● Can heartbeat
● Sends JWT in Authorization header
● Uses correct droplet_id
● Successful /udc/handshake
● Health endpoint reachable