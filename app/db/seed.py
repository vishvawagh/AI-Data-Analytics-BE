from app.db.database import get_connection

def seed_users():
    conn = get_connection()
    cursor = conn.cursor()

    users = [
        ("sales_user", "123", "sales", "user"),
        ("product_user", "123", "product", "user"),
        ("store_user", "123", "store", "user"),
        ("admin", "123", "sales", "admin")
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO users (username, password, department, role) VALUES (?, ?, ?, ?)",
        users
    )

    conn.commit()
    conn.close()