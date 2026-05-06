import asyncio
from datetime import UTC, datetime

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.modules.auth.enums import UserRole, UserStatus
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository


async def seed_owner() -> None:
    async with AsyncSessionLocal() as db:
        repo = AuthRepository(db)
        email = settings.seed_owner_email.lower()
        existing = await repo.get_user_by_email(email)

        if existing is not None:
            if existing.role != UserRole.OWNER:
                raise RuntimeError(f"Seed owner email already belongs to a {existing.role} user")

            existing.status = UserStatus.VERIFIED
            existing.tenant_id = settings.seed_tenant_id
            existing.updated_at = datetime.now(UTC)
            db.add(existing)
            await db.commit()
            print(f"Owner already exists: {email}")
            return

        owner = User(
            tenant_id=settings.seed_tenant_id,
            email=email,
            password_hash=hash_password(settings.seed_owner_password),
            role=UserRole.OWNER,
            status=UserStatus.VERIFIED,
            full_name="Owner",
        )
        db.add(owner)
        await db.commit()
        print(f"Seeded owner: {email}")


async def main() -> None:
    try:
        await seed_owner()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
