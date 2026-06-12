from app import auth, config
from app.database import SessionLocal
from app import models
import datetime

# Monkey patch config for long duration
settings = config.get_settings()
settings.JWT_EXPIRE_HOURS = 8760 # 1 year

db = SessionLocal()
admin = db.query(models.TeamMember).filter(models.TeamMember.email == "admin@fullpotential.ai").first()

if not admin:
    print("Admin not found. Creating...")
    admin = models.TeamMember(
        id="admin-01",
        email="admin@fullpotential.ai",
        name="James Sunheart",
        role="admin",
        is_admin=True,
        trust_score=100
    )
    db.add(admin)
    db.commit()

token = auth.create_access_token(admin.id, admin.email, admin.role)
print(f"MAGIC_URL: https://fullpotential.ai/dashboards/team/?view=god&auth_token={token}")











