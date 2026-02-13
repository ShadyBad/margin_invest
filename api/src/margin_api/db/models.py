"""SQLAlchemy ORM models for Margin Invest."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from margin_api.db.base import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str] = mapped_column(String(100))
    sub_industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market_cap: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    scores: Mapped[list[Score]] = relationship(back_populates="asset")
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="asset")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(50))  # google, github, etc.
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="user")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    composite_percentile: Mapped[float]
    conviction_level: Mapped[str] = mapped_column(String(20))
    signal: Mapped[str] = mapped_column(String(20))
    quality_percentile: Mapped[float] = mapped_column(default=0.0)
    value_percentile: Mapped[float] = mapped_column(default=0.0)
    momentum_percentile: Mapped[float] = mapped_column(default=0.0)
    data_coverage: Mapped[float] = mapped_column(default=1.0)
    growth_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    scored_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    asset: Mapped[Asset] = relationship(back_populates="scores")

    __table_args__ = (
        Index("ix_scores_asset_scored", "asset_id", "scored_at"),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    conviction_level: Mapped[str] = mapped_column(String(20))
    signal: Mapped[str] = mapped_column(String(20))
    entered_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    exited_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    asset: Mapped[Asset] = relationship(back_populates="recommendations")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_name: Mapped[str] = mapped_column(String(50))  # "fmp", "polygon", etc.
    encrypted_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    user: Mapped[User] = relationship(back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint("user_id", "provider_name", name="uq_user_provider"),
    )
