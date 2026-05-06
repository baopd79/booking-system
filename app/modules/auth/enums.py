"""
Auth domain enums.

Pattern: StrEnum (Python 3.11+)
- Value là string thật (JSON serialize không cần .value)
- Có IDE autocomplete (UserRole.CUSTOMER)
- Single source of truth cho cả Pydantic + DB CHECK constraint
"""

from enum import StrEnum


class UserRole(StrEnum):
    CUSTOMER = "customer"
    OWNER = "owner"


class UserStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    SUSPENDED = "suspended"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
