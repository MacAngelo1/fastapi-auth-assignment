import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv(Path(__file__).with_name(".env"))
pwd_context = CryptContext(
    schemes=[scheme.strip() for scheme in os.getenv("PASSWORD_HASHING_SCHEME", "bcrypt").split(",")],
    deprecated="auto",
)
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if len(SECRET_KEY) < 32:
    raise RuntimeError("Set SECRET_KEY to a generated value of at least 32 characters in .env.")


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    if len(plain_password.encode("utf-8")) > 72 or "\x00" in plain_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
