from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.enums import TripStatus, TripDirection
from infrastructure.database import Base


class Trip(Base):
    """Driver announces a trip on a line in a direction."""
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint('booked_seats >= 0', name='ck_trips_booked_seats_positive'),
        CheckConstraint('physical_seats >= 0', name='ck_trips_physical_seats_positive'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"), index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), index=True)
    direction: Mapped[TripDirection] = mapped_column(String(10))  # a_to_b or b_to_a
    total_seats: Mapped[int] = mapped_column(Integer, default=4)
    booked_seats: Mapped[int] = mapped_column(Integer, default=0)
    physical_seats: Mapped[int] = mapped_column(Integer, default=0)  # passengers from station (not online)
    price_per_seat: Mapped[int] = mapped_column(Integer)
    status: Mapped[TripStatus] = mapped_column(String(20), default=TripStatus.COLLECTING, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    departed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    driver: Mapped["Driver"] = relationship(back_populates="trips")
    route: Mapped["Route"] = relationship()
    bookings: Mapped[list["Booking"]] = relationship(back_populates="trip")

    @property
    def occupied(self) -> int:
        return self.booked_seats + self.physical_seats

    @property
    def seats_left(self) -> int:
        return max(0, self.total_seats - self.occupied)

    @property
    def is_full(self) -> bool:
        return self.occupied >= self.total_seats


class Booking(Base):
    """Client books a seat on a trip."""
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active, picked_up, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    trip: Mapped["Trip"] = relationship(back_populates="bookings")
    user: Mapped["User"] = relationship(back_populates="bookings")
