# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine, Base
from app import models

from app.routers import auth
from app.routers import users
from app.routers import draws
from app.routers import payments
from app.routers import deuna_manual
from app.routers import admin_payments
from app.routers import bank_accounts

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SorteaMax API V2",
    version="2.0.0",
    description="API para gestion de usuarios, sorteos, pagos y tickets de SorteaMax",
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://sorteamax-frontend.vercel.app",
    "https://sorteamax-frontend-*.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(draws.router)
app.include_router(payments.router)
app.include_router(deuna_manual.router)
app.include_router(admin_payments.router)
app.include_router(bank_accounts.router)
