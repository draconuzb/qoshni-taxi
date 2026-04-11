from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.review import Review
from core.models.driver import Driver


class ReviewService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_review(
        self,
        order_id: int,
        from_user_id: int,
        to_user_id: int,
        rating: int,
        comment: str | None = None,
    ) -> Review:
        review = Review(
            order_id=order_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            rating=rating,
            comment=comment,
        )
        self.session.add(review)
        await self.session.commit()

        # Haydovchi reytingini yangilash
        await self._update_driver_rating(to_user_id)
        return review

    async def _update_driver_rating(self, user_id: int) -> None:
        avg_result = await self.session.execute(
            select(func.avg(Review.rating)).where(Review.to_user_id == user_id)
        )
        avg_rating = avg_result.scalar()

        if avg_rating is not None:
            result = await self.session.execute(
                select(Driver).where(Driver.user_id == user_id)
            )
            driver = result.scalar_one_or_none()
            if driver:
                driver.rating = round(float(avg_rating), 2)
                await self.session.commit()
