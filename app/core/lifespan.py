from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.base import Base
from app.db.models import interview, report, turn  # noqa: F401
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
