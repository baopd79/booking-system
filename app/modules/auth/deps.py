from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenType, decode_token
from app.modules.auth.email import get_email_service
from app.modules.auth.enums import UserRole, UserStatus
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthRepository:
    return AuthRepository(db)


def get_auth_service(repo: Annotated[AuthRepository, Depends(get_auth_repository)]) -> AuthService:
    return AuthService(repo=repo, email_service=get_email_service())


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    repo: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Authentication required", error_code="AUTH_REQUIRED")

    payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid token", error_code="INVALID_TOKEN") from exc

    user = await repo.get_user_by_id(user_id)
    if user is None:
        raise UnauthorizedError("Invalid token", error_code="INVALID_TOKEN")

    if user.status == UserStatus.SUSPENDED:
        raise ForbiddenError("Account suspended", error_code="ACCOUNT_SUSPENDED")

    return user


def require_role(*roles: UserRole) -> Callable:
    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise ForbiddenError("Permission denied", error_code="INSUFFICIENT_ROLE")
        return user

    return dependency


customer_role_dependency = require_role(UserRole.CUSTOMER)


async def require_verified_customer(
    user: Annotated[User, Depends(customer_role_dependency)],
) -> User:
    if user.status != UserStatus.VERIFIED:
        raise ForbiddenError("Email not verified", error_code="EMAIL_NOT_VERIFIED")
    return user
