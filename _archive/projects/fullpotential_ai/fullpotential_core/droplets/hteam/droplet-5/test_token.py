import jwt
import datetime

with open("private_key.pem", "r") as f:
    private_key = f.read()

# Try with droplet_id 4 like your friend
payload = {
    "droplet_id": 4,
    "iat": datetime.datetime.utcnow(),
    "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
}

token = jwt.encode(payload, private_key, algorithm="RS256")
print(token)
