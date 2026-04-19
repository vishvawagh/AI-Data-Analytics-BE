from fastapi import APIRouter, Depends
from app.db.database import get_connection


router = APIRouter()

@router.get("/check-data")
def check_data():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sales LIMIT 5")
    return [dict(row) for row in cursor.fetchall()]

@router.get("/debug-join")
def debug_join():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""SELECT *
FROM sales s
JOIN products p ON s.product_id = p.product_id
LIMIT 5;"""
   
    )

    return [dict(row) for row in cursor.fetchall()]