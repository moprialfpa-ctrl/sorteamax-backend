from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut
from app.security import hash_password
from app.dependencies import get_current_admin

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    new_user = User(
        full_name=user.full_name,
        email=user.email,
        password_hash=hash_password(user.password),
        role="user"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return db.query(User).all()
