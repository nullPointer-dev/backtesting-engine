from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.models.base import Base


class User(Base):

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )
    password_hash: Mapped[str] = mapped_column(nullable=False
    )

    created_at: Mapped[datetime]

    strategies: Mapped[list["Strategy"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )