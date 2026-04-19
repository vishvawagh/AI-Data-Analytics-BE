from app.db.models import create_tables
from app.db.seed import seed_users

create_tables()
seed_users()

print("Database Initialized Successfully")