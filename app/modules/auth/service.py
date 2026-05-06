from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, GoneError, UnauthorizedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.email import EmailService
from app.modules.auth.enums import AuditOutcome, UserRole, UserStatus
from app.modules.auth.models import EmailVerificationToken, RefreshToken, User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)


class AuthService:
    def __init__(self, repo: AuthRepository, email_service: EmailService):
        self.repo = repo
        self.email_service = email_service

    async def register_customer(self, request: RegisterRequest) -> RegisterResponse:
        email = request.email.lower()
        existing = await self.repo.get_user_by_email(email)
        if existing is not None:
            raise ConflictError("Email already exists", error_code="EMAIL_ALREADY_EXISTS")

        user = User(
            tenant_id=settings.seed_tenant_id,
            email=email,
            password_hash=hash_password(request.password),
            role=UserRole.CUSTOMER,
            status=UserStatus.UNVERIFIED,
            full_name=request.full_name,
            phone=request.phone,
        )
        self.repo.add_user(user)

        plain_token = generate_secure_token()
        verification_token = EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(plain_token),
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        self.repo.add_email_verification_token(verification_token)

        try:
            await self.repo.db.commit()
        except IntegrityError as exc:
            await self.repo.db.rollback()
            raise ConflictError("Email already exists", error_code="EMAIL_ALREADY_EXISTS") from exc

        await self.email_service.send_verification_email(email, plain_token)

        return RegisterResponse(
            id=user.id,
            email=user.email,
            status=user.status,
            message="Registration successful. Please verify your email.",
            verification_token=plain_token if settings.app_debug else None,
        )

    async def verify_email(self, token: str) -> None:
        token_row = await self.repo.get_email_verification_token(hash_token(token))
        if token_row is None or token_row.used_at is not None:
            raise UnauthorizedError("Invalid verification token", error_code="INVALID_TOKEN")

        now = datetime.now(UTC)
        if token_row.expires_at <= now:
            raise GoneError("Verification token expired", error_code="VERIFICATION_TOKEN_EXPIRED")

        user = await self.repo.get_user_by_id(token_row.user_id)
        if user is None:
            raise UnauthorizedError("Invalid verification token", error_code="INVALID_TOKEN")

        user.status = UserStatus.VERIFIED
        token_row.used_at = now
        self.repo.db.add(user)
        self.repo.db.add(token_row)
        await self.repo.db.commit()

    async def login(
        self,
        request: LoginRequest,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        email = request.email.lower()
        user = await self.repo.get_user_by_email(email)

        if user is None or not verify_password(request.password, user.password_hash):
            self.repo.add_audit_log(
                event_type="auth.login",
                outcome=AuditOutcome.FAILED,
                user_id=user.id if user else None,
                ip=ip,
                user_agent=user_agent,
                metadata={"email": email},
            )
            await self.repo.db.commit()
            raise UnauthorizedError("Invalid credentials", error_code="INVALID_CREDENTIALS")

        if user.status == UserStatus.UNVERIFIED:
            self.repo.add_audit_log(
                event_type="auth.login",
                outcome=AuditOutcome.FAILED,
                user_id=user.id,
                ip=ip,
                user_agent=user_agent,
                metadata={"reason": "email_unverified"},
            )
            await self.repo.db.commit()
            raise ForbiddenError("Vui lòng xác thực email", error_code="EMAIL_NOT_VERIFIED")

        if user.status == UserStatus.SUSPENDED:
            self.repo.add_audit_log(
                event_type="auth.login",
                outcome=AuditOutcome.FAILED,
                user_id=user.id,
                ip=ip,
                user_agent=user_agent,
                metadata={"reason": "suspended"},
            )
            await self.repo.db.commit()
            raise ForbiddenError("Account suspended", error_code="ACCOUNT_SUSPENDED")

        token_response = self._issue_tokens(user, ip=ip, user_agent=user_agent)
        self.repo.add_audit_log(
            event_type="auth.login",
            outcome=AuditOutcome.SUCCESS,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )
        await self.repo.db.commit()
        return token_response

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
            user_id = UUID(payload["sub"])
        except (JWTError, ValueError, UnauthorizedError) as exc:
            raise UnauthorizedError(
                "Invalid refresh token", error_code="INVALID_REFRESH_TOKEN"
            ) from exc

        token_hash = hash_token(refresh_token)
        stored_token = await self.repo.get_active_refresh_token(token_hash)
        now = datetime.now(UTC)
        if stored_token is None or stored_token.expires_at <= now:
            raise UnauthorizedError("Invalid refresh token", error_code="INVALID_REFRESH_TOKEN")

        user = await self.repo.get_user_by_id(user_id)
        if user is None or user.status != UserStatus.VERIFIED:
            raise UnauthorizedError("Invalid refresh token", error_code="INVALID_REFRESH_TOKEN")

        stored_token.revoked_at = now
        self.repo.db.add(stored_token)
        token_response = self._issue_tokens(user)
        self.repo.add_audit_log(
            event_type="auth.refresh",
            outcome=AuditOutcome.SUCCESS,
            user_id=user.id,
        )
        await self.repo.db.commit()
        return token_response

    async def logout(
        self,
        user: User,
        refresh_token: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        if refresh_token:
            await self.repo.revoke_refresh_token(hash_token(refresh_token), revoked_at=now)
        else:
            await self.repo.revoke_all_refresh_tokens(user.id, revoked_at=now)

        self.repo.add_audit_log(
            event_type="auth.logout",
            outcome=AuditOutcome.SUCCESS,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )
        await self.repo.db.commit()

    def me(self, user: User) -> MeResponse:
        return MeResponse.model_validate(user)

    def _issue_tokens(
        self,
        user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        access_token = create_access_token(
            user.id,
            tenant_id=user.tenant_id,
            role=user.role.value,
        )
        refresh_token = create_refresh_token(
            user.id,
            tenant_id=user.tenant_id,
            role=user.role.value,
        )
        self.repo.add_refresh_token(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=datetime.now(UTC)
                + timedelta(days=settings.jwt_refresh_token_expire_days),
                user_agent=user_agent,
                ip=ip,
            )
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
