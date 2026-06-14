import jwt
import datetime

# Load your private key
with open("private_key.pem", "r") as f:
    private_key = f.read()

# JWT payload (claims)
payload = {
    "droplet_id": 5,
    "steward": "Haythem",
    "permissions": ["read", "write"],
    "iat": datetime.datetime.utcnow(),
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}

# Encode JWT using RS256
token = jwt.encode(payload, private_key, algorithm="RS256")

print(token)
