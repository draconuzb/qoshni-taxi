from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database import Base


class UserRoute(Base):
    """Many-to-many: user's favorite route lines."""
    __tablename__ = "user_routes"
    __table_args__ = (UniqueConstraint("user_id", "route_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), index=True)
    last_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)  # a_to_b or b_to_a
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="favorite_routes")
    route: Mapped["Route"] = relationship()
