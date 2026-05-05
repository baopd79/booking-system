"""
Base mixins dùng chung cho mọi model.

Pattern: Mixin (multiple inheritance) — không phải base class.
Lý do: SQLModel đã có sẵn base, dùng mixin tránh diamond problem
và linh hoạt hơn (model nào cần timestamps thì kế thừa, không thì thôi).
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field


def utcnow() -> datetime:
    """
    Trả về datetime hiện tại ở UTC, có timezone info.

    Lý do dùng UTC + timezone-aware:
    - Lưu UTC trong DB → tránh bug khi server đổi timezone
    - timezone-aware → so sánh với datetime khác không bị TypeError
    - datetime.utcnow() đã deprecated trong Python 3.12, dùng datetime.now(timezone.utc)
    """
    return datetime.now(UTC)


class TimestampMixin:
    """
    Mixin thêm 2 cột: created_at, updated_at.

    Cách dùng:
        class User(TimestampMixin, SQLModel, table=True):
            ...

    Lưu ý:
    - sa_type=DateTime(timezone=True) → Postgres lưu kiểu TIMESTAMPTZ (có TZ)
    - sa_column_kwargs={"onupdate": utcnow} → tự update mỗi lần UPDATE row
    """

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=utcnow,
            nullable=False,
        )
    )

    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=utcnow,
            onupdate=utcnow,
            nullable=False,
        )
    )


class CreatedAtMixin:
    """
    Mixin chỉ thêm created_at — cho immutable tables (token, audit log).

    Lý do tách: token tables không bao giờ UPDATE,
    có updated_at là dead column gây nhầm lẫn.
    """

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            default=utcnow,
            nullable=False,
        )
    )
