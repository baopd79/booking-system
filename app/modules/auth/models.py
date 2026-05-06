"""
Auth domain models.

3 bảng:
- users: Customer + owner gộp 1 bảng, phân qua role
- email_verification_tokens: Token verify email (TTL 24h)
- refresh_tokens: Token refresh JWT (TTL 7 ngày, có thể revoke)

Note về Tenant:
- DESIGN.md có entity `tenants`, MVP seed 1 row.
- Để giảm complexity, tenant_id là column thường (UUID, không FK).
- Khi tách Tenant model riêng (slice sau), thêm FK migration nhẹ nhàng.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, Column, DateTime, String
from sqlmodel import Field, SQLModel

from app.core.db_metadata import enum_check_constraint
from app.core.models import CreatedAtMixin, TimestampMixin
from app.modules.auth.enums import AuditOutcome, UserRole, UserStatus


# ===== User =====
class User(TimestampMixin, SQLModel, table=True):
    """
    Bảng users: gộp customer + owner, phân qua role.

    Lý do gộp 1 bảng:
    - 90% field giống nhau (email, password, name, phone)
    - Auth flow giống nhau (login, JWT)
    - Phân quyền qua role + RBAC dependency, không qua bảng riêng
    """

    __tablename__ = "users"
    __table_args__ = (
        # Naming convention sẽ tự prefix:
        # name="role" → constraint name = "ck_users_role"
        CheckConstraint(enum_check_constraint("role", UserRole), name="role"),
        CheckConstraint(enum_check_constraint("status", UserStatus), name="status"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Multi-tenant ready (DESIGN.md 6.5). MVP seed 1 tenant duy nhất.
    # Type UUID nhưng KHÔNG có FK constraint ở slice này (chưa có tenants table).
    # Slice sau khi tạo Tenant model sẽ thêm FK.
    tenant_id: UUID = Field(nullable=False, index=True)

    # Email: index=True + unique=True → naming convention sinh:
    # - ix_users_email (index)
    # - uq_users_email (unique constraint)
    email: str = Field(nullable=False, max_length=255, unique=True, index=True)
    password_hash: str = Field(nullable=False, max_length=255)

    # Enum columns: dùng sa_column vì SQLModel không tự handle Enum class.
    # CheckConstraint ở __table_args__ enforce ở DB level.
    role: UserRole = Field(sa_column=Column(String(20), nullable=False))
    status: UserStatus = Field(
        default=UserStatus.UNVERIFIED,
        sa_column=Column(String(20), nullable=False),
    )

    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)


# ===== EmailVerificationToken =====
class EmailVerificationToken(CreatedAtMixin, SQLModel, table=True):
    """
    Token verify email.

    Flow:
    1. User register → tạo token random 32 bytes → hash SHA256 → lưu hash
    2. Gửi token PLAIN qua email (link verify)
    3. User click link → verify: hash lại token + tìm trong DB
    4. Match → set user.status = 'verified', token.used_at = now

    Tại sao hash:
    - DB leak → attacker không có token thật
    - Pattern giống password (không lưu plain)
    """

    __tablename__ = "email_verification_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)

    # SHA256 hex = 64 chars
    token_hash: str = Field(nullable=False, max_length=64, unique=True, index=True)

    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


# ===== RefreshToken =====
class RefreshToken(CreatedAtMixin, SQLModel, table=True):
    """
    JWT refresh token. Lưu hash để revoke được.

    Tại sao cần lưu DB (không stateless như access token):
    - Access token: 15 phút TTL, stateless OK
    - Refresh token: 7 ngày TTL, cần revoke khi:
      + User logout
      + Password change
      + Phát hiện bị compromise

    Revoke = set revoked_at != NULL.
    Refresh request: check token tồn tại + chưa revoked + chưa expired.
    """

    __tablename__ = "refresh_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    token_hash: str = Field(nullable=False, max_length=64, unique=True, index=True)

    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Audit info — track session để debug khi cần revoke
    user_agent: str | None = Field(default=None, max_length=500)
    ip: str | None = Field(default=None, max_length=45)  # IPv6 max length


# ===== AuditLog =====
class AuditLog(CreatedAtMixin, SQLModel, table=True):
    """
    Log auth events quan trọng: login success/fail, logout, refresh token rotation.

    user_id nullable vì login fail có thể xảy ra trước khi xác định được user.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(enum_check_constraint("outcome", AuditOutcome), name="outcome"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    event_type: str = Field(nullable=False, max_length=100)
    ip: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)
    outcome: AuditOutcome = Field(sa_column=Column(String(20), nullable=False))
    audit_metadata: dict | None = Field(
        default=None,
        sa_column=Column("metadata", JSON, nullable=True),
    )
