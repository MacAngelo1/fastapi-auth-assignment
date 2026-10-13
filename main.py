from contextlib import asynccontextmanager

from fastapi import FastAPI

import models
from db_config import Base, engine
from routes.auth_routes import auth_router
from routes.notes_routes import notes_router
from routes.users_routes import users_router


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="FastAPI Authentication Assignment", lifespan=lifespan)
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router, prefix="/users")
app.include_router(notes_router, prefix="/notes")


@app.get("/")
def home():
    return {"message": "Welcome to the Notes API.", "docs": "/docs"}
