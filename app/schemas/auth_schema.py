from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str
    department: str