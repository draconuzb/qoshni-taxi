from datetime import datetime

from sqlalchemy import String, Boolean, Float, ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.enums import DriverStatus
from infrastructure.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    car_model: Mapped[str] = mapped_column(String(100))
    car_color: Mapped[str] = mapped_column(String(50))
    license_plate: Mapped[str] = mapped_column(String(20))
    status: Mapped[DriverStatus] = mapped_column(String(30), default=DriverStatus.PENDING_VERIFICATION, index=True)

    # Driver's assigned line (single route)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)

    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    consecutive_skips: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    last_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_location_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="driver")
    route: Mapped["Route | None"] = relationship(foreign_keys=[route_id])
    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")
