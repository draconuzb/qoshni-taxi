from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, DateTime, func
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
    status: Mapped[DriverStatus] = mapped_column(String(30), default=DriverStatus.VERIFIED)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="driver")
    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")
