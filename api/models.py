from __future__ import annotations
import uuid

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Column, Uuid, Enum as SQLEnum, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
import enum

class ReadingStatus(enum.Enum):
    UNREAD = "unread"
    READING = "reading"
    COMPLETED = "completed"

class User(Base):
    __tablename__ = "users"

    #id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False),
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    isbn: Mapped[str] = mapped_column(String, unique=True)
    title: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    year: Mapped[int] = mapped_column(Integer)


#class library(Base):
#    __tablename__ = "libraries"


class UserBookLink(Base):
    __tablename__ = "user_book_links"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    )

    status: Mapped[ReadingStatus] = mapped_column(SQLEnum(ReadingStatus),
                                                   default=ReadingStatus.UNREAD)


    #review: Mapped[str | None] = mapped_column(String(1000), nullable=True, default=None)

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
    )
    stars: Mapped[int] = mapped_column(
        CheckConstraint("stars >= 1 and stars <= 5", name="check_stars_range"),
    )
    review_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Relationship properties (Virtual Python-only links)
    #author: Mapped["User"] = relationship()
    #book: Mapped["Book"] = relationship()
