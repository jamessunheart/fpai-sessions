from app.database import SessionLocal
from app import models, auth
import datetime

db = SessionLocal()
email = "sarah@fullpotential.ai"
existing = db.query(models.Invitation).filter(models.Invitation.email == email).first()

if existing:
    print(f"LINK: https://fullpotential.ai/join?invite={existing.token}")
else:
    print("Creating new invite...")
    token = auth.create_invite_token(email, "member", db)
    print(f"LINK: https://fullpotential.ai/join?invite={token}")











