from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    username: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String,
        default="user"
    )

    # relationship to tickets
    tickets = relationship(
        "Ticket",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
