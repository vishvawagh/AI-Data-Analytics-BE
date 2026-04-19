from fastapi import Depends, HTTPException
from app.api.auth import get_current_user


def get_admin_user(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user