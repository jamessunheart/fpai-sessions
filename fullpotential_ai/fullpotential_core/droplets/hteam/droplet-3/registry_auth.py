import os, jwt
from fastapi import HTTPException

JWT_SECRET = os.getenv("JWT_SHARED_SECRET","")

def verify_token(token: str):
    try:
        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            audience="registry"   # <= required AUD
        )
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="invalid_audience")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"unauthorized: {e}")
