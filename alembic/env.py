"""
Alembic env — apply naming convention TRƯỚC khi import models.
MVP: dùng sync driver (psycopg2) cho migration cho đơn giản.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import settings
from app.core.db_metadata import NAMING_CONVENTION

# Alembic config object
config = context.config
config.set_main_option("sqlalchemy.url", str(settings.database_url_sync))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ===== Apply naming convention TRƯỚC khi import models =====
# Lý do: SQLModel.metadata phải có convention SẴN khi class model được parse,
# nếu không các constraint sẽ lấy tên random.
from sqlmodel import SQLModel  # noqa: E402

SQLModel.metadata.naming_convention = NAMING_CONVENTION  # type: ignore[assignment]

# ===== Import models =====
# Mỗi khi thêm module mới có model → thêm import vào đây.
from app.modules.auth.models import *  # noqa: F401, F403, E402

# Future modules (uncomment khi đến slice tương ứng):
# from app.modules.facility.models import *  # noqa: F401, F403, E402
# from app.modules.booking.models import *  # noqa: F401, F403, E402
# from app.modules.payment.models import *  # noqa: F401, F403, E402
# from app.modules.notification.models import *  # noqa: F401, F403, E402

target_metadata = SQLModel.metadata


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
