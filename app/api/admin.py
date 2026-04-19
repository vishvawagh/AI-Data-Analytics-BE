from fastapi import APIRouter, Depends, HTTPException
from app.db.database import get_connection
from app.api.auth_dependency import get_admin_user

router = APIRouter(prefix="/admin", tags=["Admin"])


# ✅ CREATE USER
@router.post("/create-user")
def create_user(data: dict, admin=Depends(get_admin_user)):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (username, password, department, role)
        VALUES (?, ?, ?, ?)
    """, (
        data["username"],
        data["password"],
        data["department"],
        data.get("role", "user")
    ))

    conn.commit()
    conn.close()

    return {"message": "User created successfully"}


# 🔥 DELETE USER BY USERNAME
@router.delete("/delete-user/{username}")
def delete_user(username: str, admin=Depends(get_admin_user)):

    conn = get_connection()
    cursor = conn.cursor()

    # check if user exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    # delete user
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

    return {"message": f"User '{username}' deleted successfully"}

@router.get("/users")
def get_users(admin=Depends(get_admin_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, department, role FROM users")
    rows = cursor.fetchall()

    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "username": row[1],
            "department": row[2],
            "role": row[3]
        })

    conn.close()

    return {"users": users}