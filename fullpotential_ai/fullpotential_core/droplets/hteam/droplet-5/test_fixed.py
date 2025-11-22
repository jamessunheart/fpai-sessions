import jwt
import time

# Load private key
with open("private_key.pem", "r") as f:
    private_key = f.read()

# JWT payload with integer timestamps
now = int(time.time())
payload = {
    "droplet_id": 5,
    "steward": "Haythem",
    "permissions": ["read", "write"],
    "iat": now,
    "exp": now + 86400  # 24 hours
}

# Generate RS256 token
token = jwt.encode(payload, private_key, algorithm="RS256")
print(token)
