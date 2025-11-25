from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.db.base import Base


class Geofence(Base):
    __tablename__ = "geofences"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    polygon_geojson: Mapped[str]
