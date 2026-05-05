"""
Alembic env — Phase 3 sẽ import models từ modules.
MVP: dùng sync driver (psycopg2) cho migration cho đơn giản.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import settings

# Alembic config object
config = context.config

# Override URL từ settings (sync URL cho psycopg2)
config.set_main_option("sqlalchemy.url", str(settings.database_url_sync))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ===== Import metadata =====
# Phase 3: import từng module models, ví dụ:
# from app.modules.auth.models import *  # noqa
# from app.modules.facility.models import *  # noqa
# Hiện tại chưa có model nào, target_metadata = None
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generate SQL script."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — apply trực tiếp lên DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
