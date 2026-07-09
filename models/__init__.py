"""
SQLAlchemy ORM models for the bot database.
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Index, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column("created_at", server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column("updated_at")
    name: Mapped[str | None] = mapped_column("name")
    description: Mapped[str | None] = mapped_column("description")
    type: Mapped[str | None] = mapped_column("type")  # public, private, etc


class User(Base):
    """Telegram user."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column("created_at", server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column("updated_at")
    first_name: Mapped[str | None] = mapped_column("first_name")
    last_name: Mapped[str | None] = mapped_column("last_name")
    username: Mapped[str | None] = mapped_column("username")
    spam_score: Mapped[int] = mapped_column("spam_score", default=0)


class Message(Base):
    """Logged message from a group."""

    __tablename__ = "message"

    id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column("group_id", BigInteger, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column("created_at", server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column("updated_at")
    user_id: Mapped[int] = mapped_column("user_id", BigInteger, index=True)
    type: Mapped[str] = mapped_column("type")  # text, photo, etc
    text: Mapped[str | None] = mapped_column("text")
    params: Mapped[dict | None] = mapped_column("params", JSON)
    spam_score: Mapped[int] = mapped_column("spam_score", default=0)

    __table_args__ = (
        # Композитный индекс для быстрого подсчёта сообщений пользователя в группе
        Index("ix_message_group_user", "group_id", "user_id"),
    )


class ConfirmedUser(Base):
    """User who passed verification in a specific group."""

    __tablename__ = "confirmed_user"

    id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column("group_id", BigInteger)
    user_id: Mapped[int] = mapped_column("user_id", BigInteger)

    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_confirmed_user_group_user"),)


class ConfirmCode(Base):
    """Pending verification code for a user in a group."""

    __tablename__ = "confirm_code"

    id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column("group_id", BigInteger)
    user_id: Mapped[int] = mapped_column("user_id", BigInteger)
    code: Mapped[str] = mapped_column("code")

    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_confirm_code_group_user"),)


class SpamTraining(Base):
    """Known spam message for ML training."""

    __tablename__ = "spam_training"

    id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    is_spam: Mapped[bool] = mapped_column("is_spam")
    text: Mapped[str] = mapped_column("text")


class DisabledWord(Base):
    __tablename__ = "disabled_word"

    id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True)
    term: Mapped[str] = mapped_column("term")
    rule_type: Mapped[str] = mapped_column("rule_type")
    spam_score: Mapped[int] = mapped_column("spam_score", default=0)
