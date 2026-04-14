from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.enums import TripStatus, TripDirection, BookingStatus
from infrastructure.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"))
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"))
    direction: Mapped[TripDirection] = mapped_column(String(10))
    total_seats: Mapped[int] = mapped_column(Integer, default=4)
    booked_seats: Mapped[int] = mapped_column(Integer, default=0)
    price_per_seat: Mapped[int] = mapped_column(Integer)
    status: Mapped[TripStatus] = mapped_column(String(20), default=TripStatus.COLLECTING)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    departed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    driver: Mapped["Driver"] = relationship(back_populates="trips")
    route: Mapped["Route"] = relationship()
    bookings: Mapped[list["Booking"]] = relationship(back_populates="trip")

    @property
    def seats_left(self) -> int:
        return max(0, self.total_seats - self.booked_seats)

    @property
    def is_full(self) -> bool:
        return self.booked_seats >= self.total_seats


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[BookingStatus] = mapped_column(String(20), default=BookingStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    trip: Mapped["Trip"] = relationship(back_populates="bookings")
    user: Mapped["User"] = relationship(back_populates="bookings")
