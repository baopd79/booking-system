from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: datetime = Field(  # type: ignore[call-arg]
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"nullable": False},
    )
    updated_at: datetime = Field(  # type: ignore[call-arg]
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"nullable": False, "onupdate": utcnow},
    )


class CreatedAtMixin:
    created_at: datetime = Field(  # type: ignore[call-arg]
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"nullable": False},
    )
