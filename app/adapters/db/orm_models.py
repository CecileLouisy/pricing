"""Modèles SQLAlchemy — mapping tables ↔ objets.

Ils vivent uniquement dans la couche adapters/db. Les repositories convertissent
vers les entités du domaine avant d'exposer aux use cases.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GridORM(Base):
    __tablename__ = "price_grid"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    free_period_min: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    rates: Mapped[list["RateORM"]] = relationship(
        back_populates="grid",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RateORM(Base):
    __tablename__ = "rate"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    grid_id: Mapped[str] = mapped_column(String(36), ForeignKey("price_grid.id"), nullable=False)
    zone: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    hourly_rate_eur: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    grid: Mapped["GridORM"] = relationship(back_populates="rates")


class QuoteORM(Base):
    __tablename__ = "quote"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    grid_id: Mapped[str] = mapped_column(String(36), ForeignKey("price_grid.id"), nullable=False)
    zone: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_eur: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    breakdown_json: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
