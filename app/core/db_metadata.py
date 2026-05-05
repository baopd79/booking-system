"""
Database metadata helpers — naming convention + utility cho mọi module.

Lý do tách file riêng:
- Tránh circular import (alembic/env.py + app/modules/*/models.py đều cần)
- Single source of truth: chỉ 1 nơi định nghĩa convention
- Helper enum_check_constraint dùng cho mọi module có Enum + CHECK
"""

from enum import Enum

# ===== Naming convention =====
# Pattern tên constraint sau khi apply:
# - pk_users
# - fk_refresh_tokens_user_id_users
# - uq_users_email
# - ix_users_email
# - ck_users_role
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# ===== Enum check constraint helper =====
def enum_check_constraint(column: str, enum_class: type[Enum]) -> str:
    """
    Sinh SQL CHECK constraint từ Enum class.

    Lợi: thêm value mới vào enum → constraint tự update,
    không cần sửa string SQL ở 2 chỗ (single source of truth).

    Example:
        from enum import Enum
        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        enum_check_constraint("status", Status)
        # → "status IN ('active', 'inactive')"
    """
    values = ", ".join(f"'{e.value}'" for e in enum_class)
    return f"{column} IN ({values})"
