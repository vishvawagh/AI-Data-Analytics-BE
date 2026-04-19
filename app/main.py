from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, query, health, walkthrough

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.auth import router as auth_router

from app.api.admin import router as admin_router

app.include_router(admin_router)

app.include_router(auth_router)


app.include_router(query.router)
app.include_router(health.router)
app.include_router(walkthrough.router)