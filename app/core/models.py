from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(UTC)


def created_at_col():
    return Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


def updated_at_col():
    return Column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class TimestampMixin:
    created_at: datetime = Field(sa_column=created_at_col())
    updated_at: datetime = Field(sa_column=updated_at_col())


class CreatedAtMixin:
    created_at: datetime = Field(sa_column=created_at_col())
