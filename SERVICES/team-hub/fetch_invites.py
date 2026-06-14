from app.database import SessionLocal
from app import models

db = SessionLocal()
invites = db.query(models.Invitation).filter(models.Invitation.used == False).all()

print("--- PENDING INVITES ---")
for inv in invites:
    print(f"Email: {inv.email} | Link: https://fullpotential.ai/join?invite={inv.token}")
if not invites:
    print("No pending invites found.")











