from app.db.database import get_connection

def execute_sql(sql: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(sql)
    rows = cursor.fetchall()

    conn.close()

    return [dict(row) for row in rows]