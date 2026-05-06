from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.modules.auth.enums import AuditOutcome
from app.modules.auth.models import AuditLog, EmailVerificationToken, RefreshToken, User


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(col(User.email) == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(col(User.id) == user_id))
        return result.scalar_one_or_none()

    def add_user(self, user: User) -> User:
        self.db.add(user)
        return user

    def add_email_verification_token(
        self,
        token: EmailVerificationToken,
    ) -> EmailVerificationToken:
        self.db.add(token)
        return token

    async def get_email_verification_token(
        self,
        token_hash: str,
    ) -> EmailVerificationToken | None:
        result = await self.db.execute(
            select(EmailVerificationToken).where(
                col(EmailVerificationToken.token_hash) == token_hash,
            )
        )
        return result.scalar_one_or_none()

    def add_refresh_token(self, refresh_token: RefreshToken) -> RefreshToken:
        self.db.add(refresh_token)
        return refresh_token

    async def get_active_refresh_token(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(
                col(RefreshToken.token_hash) == token_hash,
                col(RefreshToken.revoked_at).is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_hash: str, revoked_at: datetime) -> int:
        refresh_token = await self.get_active_refresh_token(token_hash)
        if refresh_token is None:
            return 0

        refresh_token.revoked_at = revoked_at
        self.db.add(refresh_token)
        return 1

    async def revoke_all_refresh_tokens(self, user_id: UUID, revoked_at: datetime) -> int:
        result = await self.db.execute(
            select(RefreshToken).where(
                col(RefreshToken.user_id) == user_id,
                col(RefreshToken.revoked_at).is_(None),
            )
        )
        tokens = list(result.scalars().all())
        for token in tokens:
            token.revoked_at = revoked_at
            self.db.add(token)
        return len(tokens)

    def add_audit_log(
        self,
        event_type: str,
        outcome: AuditOutcome,
        user_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            ip=ip,
            user_agent=user_agent,
            outcome=outcome,
            audit_metadata=metadata,
            created_at=datetime.now(UTC),
        )
        self.db.add(audit_log)
        return audit_log
