from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, token: RefreshToken) -> None:
        self.db.add(token)

    async def flush(self) -> None:
        await self.db.flush()

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()
