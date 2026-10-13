from fastapi import APIRouter, Depends, Response
from sqlalchemy import select

from db_config import get_db
from dependencies import get_current_user, require_admin
from models import User
from schemas import UserResponse, UserUpdate
from security import hash_password
from utils import commit_user_changes

users_router = APIRouter(tags=["Users"])


@users_router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@users_router.get("/", response_model=list[UserResponse])
def get_all_users(admin: User = Depends(require_admin), db=Depends(get_db)):
    return db.execute(select(User).order_by(User.id)).scalars().all()


@users_router.put("/me", response_model=UserResponse)
def update_my_profile(body: UserUpdate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    changes = body.model_dump(exclude_unset=True)
    if "password" in changes:
        current_user.password = hash_password(changes.pop("password"))
    if "email" in changes:
        changes["email"] = str(changes["email"]).lower()
    for field, value in changes.items():
        setattr(current_user, field, value)
    commit_user_changes(db)
    db.refresh(current_user)
    return current_user


@users_router.delete("/me", status_code=204)
def delete_my_profile(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    db.delete(current_user)
    db.commit()
    return Response(status_code=204)
