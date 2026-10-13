from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from db_config import get_db
from dependencies import authentication_error
from models import User
from schemas import TokenResponse, UserCreate, UserResponse
from security import create_access_token, hash_password, verify_password
from utils import commit_user_changes

auth_router = APIRouter(tags=["Authentication"])


@auth_router.post("/register", status_code=201, response_model=UserResponse)
def register_user(body: UserCreate, db=Depends(get_db)):
    user = User(username=body.username, email=str(body.email).lower(), full_name=body.full_name,
                password=hash_password(body.password), disabled=False, role="user")
    db.add(user)
    commit_user_changes(db)
    db.refresh(user)
    return user


@auth_router.post("/token", response_model=TokenResponse)
def login_user(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user = db.execute(select(User).where(User.username == form.username)).scalar_one_or_none()
    if user is None or not verify_password(form.password, user.password):
        raise authentication_error("Invalid username or password.")
    if user.disabled:
        raise HTTPException(status_code=403, detail="Your account is disabled.")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}
