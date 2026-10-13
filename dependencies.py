import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select

from db_config import get_db
from models import Note, User
from security import ALGORITHM, SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def authentication_error(message):
    return HTTPException(status_code=401, detail=message, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["sub", "iat", "exp"]})
        user_id = int(payload["sub"])
    except ExpiredSignatureError:
        raise authentication_error("Token has expired. Log in again.")
    except (InvalidTokenError, ValueError, TypeError):
        raise authentication_error("Invalid authentication token.")

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise authentication_error("User no longer exists.")
    if user.disabled:
        raise HTTPException(status_code=403, detail="Your account is disabled.")
    return user


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def get_note_or_404(note_id: int, db=Depends(get_db)):
    note = db.execute(select(Note).where(Note.id == note_id)).scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return note


def require_note_owner(
    current_user: User = Depends(get_current_user),
    note: Note = Depends(get_note_or_404),
):
    if note.owner != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the owner or an admin can modify this note.")
    return note
