from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine, Base
from app import models

from app.routers import auth, users, draws, payments, deuna_manual, admin_payments, bank_accounts, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SorteaMax API V2",
    version="2.0.0",
    description="API para gestion de usuarios, sorteos, pagos, tickets y administracion de SorteaMax",
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://sorteamax-frontend.vercel.app",
    "https://sorteamax-frontend-mv401go08-moprialfpa-ctrls-projects.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(draws.router)
app.include_router(payments.router)
app.include_router(deuna_manual.router)
app.include_router(admin_payments.router)
app.include_router(bank_accounts.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {
        "message": "SorteaMax API V2 funcionando",
        "modules": ["auth", "users", "draws", "payments", "deuna_manual", "admin_payments", "bank_accounts", "admin"],
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/db")
def health_db():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}