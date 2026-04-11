from datetime import datetime

from sqlalchemy import String, Float, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="")        # line name e.g. "1-chi yo'nalish"
    region: Mapped[str] = mapped_column(String(50), default="")       # viloyat ID
    district: Mapped[str] = mapped_column(String(50), default="")     # tuman ID
    from_name: Mapped[str] = mapped_column(String(255), default="")   # A joy
    to_name: Mapped[str] = mapped_column(String(255), default="")     # B joy
    price: Mapped[int] = mapped_column(Integer)                       # so'mda
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Keep old columns for backward compat with existing data
    from_region: Mapped[str] = mapped_column(String(50), default="")
    from_district: Mapped[str] = mapped_column(String(50), default="")
    to_region: Mapped[str] = mapped_column(String(50), default="")
    to_district: Mapped[str] = mapped_column(String(50), default="")

    @property
    def display_name(self) -> str:
        if self.name:
            return f"{self.name}: {self.from_name} ↔ {self.to_name}"
        return f"{self.from_name} ↔ {self.to_name}"
