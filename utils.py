from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def commit_user_changes(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists.")
