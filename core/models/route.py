from datetime import datetime

from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    region: Mapped[str] = mapped_column(String(50), default="")
    district: Mapped[str] = mapped_column(String(50), default="")
    from_name: Mapped[str] = mapped_column(String(255), default="")
    to_name: Mapped[str] = mapped_column(String(255), default="")
    price: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def display_name(self) -> str:
        if self.name:
            return f"{self.name}: {self.from_name} ↔ {self.to_name}"
        return f"{self.from_name} ↔ {self.to_name}"
