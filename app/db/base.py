from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models after Base definition so metadata can collect them.
from app.db.models.interview import Interview  # noqa: E402,F401
from app.db.models.report import Report  # noqa: E402,F401
from app.db.models.turn import Turn  # noqa: E402,F401
