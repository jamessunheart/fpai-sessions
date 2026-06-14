from app.database import SessionLocal
from app.auth import create_magic_link
from app import models

db = SessionLocal()
email = "james@fullpotential.ai"

# Ensure user exists
user = db.query(models.TeamMember).filter(models.TeamMember.email == email).first()
if not user:
    print(f"User {email} not found, creating...")
    user = models.TeamMember(email=email, role="owner", trust_score=100)
    db.add(user)
    db.commit()

token, expires = create_magic_link(email, db)
print(f"\nMAGIC LINK (Valid for 15 mins):")
print(f"https://fullpotential.ai/dashboards/team/auth/verify?token={token}")
print(f"\nUse this link to log in. Your session will now last 30 days.")
db.close()

