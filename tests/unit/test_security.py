"""
Unit tests cho app/core/security.py.

Tổ chức theo function. Mỗi function 2-3 test cases:
- Happy path
- Edge case
- Failure case (raise exception)

Pattern pytest:
- Hàm test bắt đầu bằng `test_`
- Class group bằng `Test<Subject>` — gom test theo subject
- pytest.raises để assert exception
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from jose import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
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


# ===== Password hashing =====
class TestPasswordHashing:
    def test_hash_password_returns_different_value(self):
        """Hash phải khác plain password."""
        password = "secret123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_hash_password_with_same_input_returns_different_hash(self):
        """
        Bcrypt salt random → 2 lần hash cùng password → 2 hash khác.
        Đây là behavior bảo mật quan trọng — chống rainbow table.
        """
        password = "secret123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # khác nhau do salt khác

    def test_verify_password_correct_returns_true(self):
        password = "secret123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_wrong_returns_false(self):
        hashed = hash_password("secret123")

        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty_string(self):
        """Edge case: password rỗng."""
        hashed = hash_password("")

        assert verify_password("", hashed) is True
        assert verify_password("not_empty", hashed) is False


# ===== JWT =====
class TestJWT:
    def test_create_access_token_returns_string(self):
        user_id = uuid4()
        token = create_access_token(user_id)

        assert isinstance(token, str)
        # JWT format: header.payload.signature → 3 phần
        assert len(token.split(".")) == 3

    def test_access_token_contains_correct_claims(self):
        """Verify payload chứa đúng claims chốt: sub, exp, iat, type."""
        user_id = uuid4()
        token = create_access_token(user_id)

        # Decode raw (không qua decode_token để verify nội dung thuần)
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        # Đảm bảo KHÔNG có claim thừa (theo quyết định minimum claims)
        assert set(payload.keys()) == {"sub", "exp", "iat", "type"}

    def test_refresh_token_has_type_refresh(self):
        token = create_refresh_token(uuid4())

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["type"] == "refresh"

    def test_refresh_token_has_longer_expiry_than_access(self):
        """Refresh token (7 ngày) phải sống lâu hơn access (15ph)."""
        user_id = uuid4()
        access = create_access_token(user_id)
        refresh = create_refresh_token(user_id)

        access_payload = jwt.decode(
            access, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        refresh_payload = jwt.decode(
            refresh, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        assert refresh_payload["exp"] > access_payload["exp"]

    def test_decode_access_token_success(self):
        user_id = uuid4()
        token = create_access_token(user_id)

        payload = decode_token(token, expected_type=TokenType.ACCESS)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_decode_refresh_token_success(self):
        user_id = uuid4()
        token = create_refresh_token(user_id)

        payload = decode_token(token, expected_type=TokenType.REFRESH)

        assert payload["sub"] == str(user_id)

    def test_decode_invalid_token_raises_unauthorized(self):
        """Token rác → reject."""
        with pytest.raises(UnauthorizedError) as exc_info:
            decode_token("not.a.valid.token", expected_type=TokenType.ACCESS)

        assert exc_info.value.error_code == "INVALID_TOKEN"

    def test_decode_token_with_wrong_secret_raises_unauthorized(self):
        """Token sign bằng secret khác → reject (chống forge)."""
        # Tạo token với secret KHÁC
        bad_token = jwt.encode(
            {"sub": str(uuid4()), "type": "access", "exp": 9999999999, "iat": 0},
            "wrong_secret_key_must_be_long_enough_for_validation",
            algorithm="HS256",
        )

        with pytest.raises(UnauthorizedError):
            decode_token(bad_token, expected_type=TokenType.ACCESS)

    def test_decode_access_token_when_expecting_refresh_raises(self):
        """Access token gửi vào endpoint mong refresh → reject."""
        token = create_access_token(uuid4())

        with pytest.raises(UnauthorizedError) as exc_info:
            decode_token(token, expected_type=TokenType.REFRESH)

        assert exc_info.value.error_code == "INVALID_TOKEN_TYPE"

    def test_decode_refresh_token_when_expecting_access_raises(self):
        """Ngược lại: refresh token gửi vào endpoint mong access → reject."""
        token = create_refresh_token(uuid4())

        with pytest.raises(UnauthorizedError) as exc_info:
            decode_token(token, expected_type=TokenType.ACCESS)

        assert exc_info.value.error_code == "INVALID_TOKEN_TYPE"

    def test_decode_expired_token_raises(self):
        """Token đã expire → reject."""
        # Manually tạo token đã expire
        expired_payload = {
            "sub": str(uuid4()),
            "type": "access",
            "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedError):
            decode_token(expired_token, expected_type=TokenType.ACCESS)

    def test_decode_token_missing_sub_raises(self):
        """Token thiếu 'sub' → reject (defensive check)."""
        # Tạo token không có 'sub'
        bad_payload = {
            "type": "access",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        }
        bad_token = jwt.encode(
            bad_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedError) as exc_info:
            decode_token(bad_token, expected_type=TokenType.ACCESS)

        assert exc_info.value.error_code == "INVALID_TOKEN"


# ===== Token hashing =====
class TestTokenHashing:
    def test_generate_secure_token_default_length(self):
        token = generate_secure_token()

        # token_urlsafe(32) → ~43 chars (base64 of 32 bytes)
        assert isinstance(token, str)
        assert len(token) >= 40

    def test_generate_secure_token_returns_unique(self):
        """Random → 2 token khác nhau gần như chắc chắn."""
        tokens = {generate_secure_token() for _ in range(100)}

        # 100 unique values trong set → không có duplicate
        assert len(tokens) == 100

    def test_hash_token_returns_64_char_hex(self):
        """SHA256 hex = 64 chars."""
        hashed = hash_token("any_token_value")

        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_token_deterministic(self):
        """
        Cùng input → cùng output.
        KHÁC bcrypt: bcrypt có salt → khác. SHA256 không salt → giống.
        Đây là property cần thiết để DB lookup token được.
        """
        token = "abc123"
        hash1 = hash_token(token)
        hash2 = hash_token(token)

        assert hash1 == hash2

    def test_hash_token_different_inputs_different_hashes(self):
        assert hash_token("token1") != hash_token("token2")

    def test_full_token_workflow(self):
        """
        End-to-end workflow:
        1. Server generate plain token
        2. Server hash → lưu DB
        3. User gửi plain token lại
        4. Server hash plain → match với hash đã lưu
        """
        # Step 1: server tạo
        plain = generate_secure_token()
        # Step 2: lưu hash
        stored_hash = hash_token(plain)

        # Step 3 & 4: user gửi lại plain, server verify
        received_plain = plain  # giả lập user gửi đúng token
        assert hash_token(received_plain) == stored_hash

        # Wrong token → không match
        wrong_plain = generate_secure_token()
        assert hash_token(wrong_plain) != stored_hash
