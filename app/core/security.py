"""
Security utilities — pure functions, không depend vào DB.

Chia 3 nhóm:
1. Password hashing (bcrypt direct — passlib depend stdlib `crypt` đã bị
   removed ở Python 3.13)
2. JWT encode/decode (HS256)
3. Token hashing (SHA256) — cho email verification & refresh token

Pattern: stateless functions. DB operations để ở repository/service layer.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

# ===== Password hashing =====
# Dùng bcrypt trực tiếp.
# bcrypt limit: max 72 bytes input. Nếu password dài hơn → tự truncate
# (không error). Đây là known limitation — best practice: validate password
# length ở Pydantic schema (max 64 chars).


def hash_password(plain_password: str) -> str:
    """
    Hash password bằng bcrypt với salt random.

    bcrypt tự sinh salt → 2 lần hash cùng password → 2 hash khác nhau.
    Cost factor mặc định: 12 (~250ms hash time — đủ slow chống brute force).

    Output format: $2b$12$<salt22chars><hash31chars> (60 chars total).
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    So sánh plain password với hash. Return False nếu hash format sai.

    bcrypt.checkpw constant-time comparison bên trong → tránh timing attack.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        # hashed_password format sai (vd không phải bcrypt hash) → reject
        return False


# ===== JWT =====
class TokenType(StrEnum):
    """
    Phân biệt access vs refresh token trong claim 'type'.

    Lý do cần 'type':
    - Access token: dùng gọi API (15ph TTL)
    - Refresh token: chỉ dùng ở /auth/refresh (7 ngày TTL)
    - Phải reject access token gửi vào /auth/refresh và ngược lại.
    """

    ACCESS = "access"
    REFRESH = "refresh"


def _create_token(
    user_id: UUID,
    token_type: TokenType,
    expires_in: timedelta,
) -> str:
    """
    Internal helper: tạo JWT với minimum claims.

    Claims:
    - sub: user_id (string vì JWT spec yêu cầu sub là string)
    - exp: expiration timestamp (UTC seconds)
    - iat: issued at timestamp
    - type: access | refresh

    Không include email/role/tenant_id (xem ADR: minimum claims).
    """
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
        "type": token_type.value,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    """Access token: 15 phút TTL (cấu hình ở settings)."""
    return _create_token(
        user_id=user_id,
        token_type=TokenType.ACCESS,
        expires_in=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: UUID) -> str:
    """Refresh token: 7 ngày TTL (cấu hình ở settings)."""
    return _create_token(
        user_id=user_id,
        token_type=TokenType.REFRESH,
        expires_in=timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """
    Decode + verify JWT.

    Verify:
    1. Signature đúng (HS256 với secret key)
    2. Token chưa expire (jose tự check 'exp')
    3. Type khớp expected_type (chống misuse access vs refresh)

    Raise UnauthorizedError nếu fail bất kỳ check nào.
    Service layer catch exception này để trả 401.

    Lý do raise UnauthorizedError thay vì JWTError:
    - JWTError là exception của jose library (low-level)
    - UnauthorizedError là domain exception, mapping tới HTTP 401
    - Service không cần biết về jose internals
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as e:
        # Wrap mọi JWT error → domain exception
        raise UnauthorizedError("Invalid token", error_code="INVALID_TOKEN") from e

    # Verify type — chống dùng access token ở /auth/refresh và ngược lại
    token_type = payload.get("type")
    if token_type != expected_type.value:
        raise UnauthorizedError(
            f"Invalid token type: expected {expected_type.value}, got {token_type}",
            error_code="INVALID_TOKEN_TYPE",
        )

    # Verify sub tồn tại (defensive — jose không enforce required claims)
    if "sub" not in payload:
        raise UnauthorizedError("Token missing 'sub' claim", error_code="INVALID_TOKEN")

    return payload


# ===== Token hashing (SHA256) =====
# Cho email verification token & refresh token storage.
# KHÁC password hashing:
# - Password: hash 1 chiều, verify bằng compare hash mới với hash lưu.
# - Token: hash 1 chiều, verify bằng search DB với hash của token user gửi.
#
# Tại sao SHA256 mà không bcrypt?
# - Token đã random 32 bytes → entropy cao, không cần slow hash chống brute force
# - Cần performance để search DB nhanh (index trên hash)
# - bcrypt mỗi hash khác nhau (salt) → không index search được


def generate_secure_token(num_bytes: int = 32) -> str:
    """
    Tạo random token URL-safe, dùng cho:
    - Email verification: gửi qua link (browser-safe)
    - Refresh token: lưu plain ở client cookie/storage

    secrets.token_urlsafe → cryptographically secure random
    32 bytes → ~43 chars sau base64 → đủ entropy (256 bits)
    """
    return secrets.token_urlsafe(num_bytes)


def hash_token(token: str) -> str:
    """
    Hash token bằng SHA256 → 64 chars hex.

    Match với schema: token_hash VARCHAR(64).

    Workflow:
    1. Server generate token random → gửi PLAIN cho user (email/response)
    2. Server hash token → lưu HASH vào DB
    3. User submit token → server hash lại → search DB với hash
    4. Match → token valid

    DB leak → attacker không có token plain.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
