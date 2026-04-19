from fastapi import APIRouter, Response, Request, HTTPException
from app.db.database import get_connection
from app.core.session import create_session, get_user

router = APIRouter()


# 🔐 LOGIN
@router.post("/login")
def login(data: dict, response: Response):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (data["username"],))
    user = cursor.fetchone()

    if not user or user["password"] != data["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ✅ Convert sqlite row → dict
    user_dict = dict(user)

    # ✅ Create session
    session_id = create_session(user_dict)

    # 🔥 IMPORTANT COOKIE FIX
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",   # 🔥 important for localhost
        secure=False      # 🔥 keep False for local dev
    )

    return {"message": "Login successful"}


# 🔐 GET CURRENT USER (Dependency)
def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")

    user = get_user(session_id)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user


# 🔍 GET USER INFO
@router.get("/me")
def get_me(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id:
        return {"error": "Not logged in"}

    user = get_user(session_id)

    if not user:
        return {"error": "Invalid session"}

    return {
        "username": user["username"],
        "role": user["role"],
        "department": user["department"]
    }