import sqlite3
import os

# 🔥 Path to DB file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "app", "db", "analytics.db")


# ✅ Get DB connection
def get_connection():
    conn = sqlite3.connect(DB_PATH)

    # Return rows as dictionary (VERY IMPORTANT)
    conn.row_factory = sqlite3.Row

    return conn