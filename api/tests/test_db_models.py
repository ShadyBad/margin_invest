"""Tests for database models using SQLite in-memory."""

from __future__ import annotations

import pytest
from margin_api.db.base import Base
from margin_api.db.models import ApiKey, Asset, Recommendation, Score, User
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


class TestAssetModel:
    def test_asset_table_name(self):
        assert Asset.__tablename__ == "assets"

    def test_asset_columns(self):
        columns = {c.name for c in Asset.__table__.columns}
        assert "id" in columns
        assert "ticker" in columns
        assert "name" in columns
        assert "sector" in columns
        assert "market_cap" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_ticker_unique_constraint(self):
        ticker_col = Asset.__table__.columns["ticker"]
        assert ticker_col.unique is True


class TestUserModel:
    def test_user_table_name(self):
        assert User.__tablename__ == "users"

    def test_user_columns(self):
        columns = {c.name for c in User.__table__.columns}
        assert "id" in columns
        assert "email" in columns
        assert "name" in columns
        assert "provider" in columns

    def test_email_unique_constraint(self):
        email_col = User.__table__.columns["email"]
        assert email_col.unique is True


class TestScoreModel:
    def test_score_table_name(self):
        assert Score.__tablename__ == "scores"

    def test_score_columns(self):
        columns = {c.name for c in Score.__table__.columns}
        expected = {
            "id",
            "asset_id",
            "composite_percentile",
            "conviction_level",
            "signal",
            "quality_percentile",
            "value_percentile",
            "momentum_percentile",
            "data_coverage",
            "growth_stage",
            "scored_at",
        }
        assert expected.issubset(columns)

    def test_score_has_asset_fk(self):
        asset_id_col = Score.__table__.columns["asset_id"]
        fks = list(asset_id_col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "assets.id"


class TestRecommendationModel:
    def test_recommendation_table_name(self):
        assert Recommendation.__tablename__ == "recommendations"

    def test_recommendation_columns(self):
        columns = {c.name for c in Recommendation.__table__.columns}
        assert "asset_id" in columns
        assert "conviction_level" in columns
        assert "is_active" in columns
        assert "entered_at" in columns
        assert "exited_at" in columns


class TestApiKeyModel:
    def test_api_key_table_name(self):
        assert ApiKey.__tablename__ == "api_keys"

    def test_api_key_columns(self):
        columns = {c.name for c in ApiKey.__table__.columns}
        assert "user_id" in columns
        assert "provider_name" in columns
        assert "encrypted_key" in columns

    def test_user_provider_unique_constraint(self):
        constraints = [
            c.name
            for c in ApiKey.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_user_provider" in constraints


class TestRelationships:
    def test_asset_has_scores_relationship(self):
        assert hasattr(Asset, "scores")

    def test_asset_has_recommendations_relationship(self):
        assert hasattr(Asset, "recommendations")

    def test_user_has_api_keys_relationship(self):
        assert hasattr(User, "api_keys")

    def test_score_has_asset_relationship(self):
        assert hasattr(Score, "asset")


class TestTableCreation:
    """Test that all tables can be created successfully."""

    @pytest.fixture()
    def sync_engine(self):
        return create_engine("sqlite:///:memory:")

    def test_create_all_tables(self, sync_engine):
        Base.metadata.create_all(sync_engine)
        table_names = set(Base.metadata.tables.keys())
        assert "assets" in table_names
        assert "users" in table_names
        assert "scores" in table_names
        assert "recommendations" in table_names
        assert "api_keys" in table_names

    def test_insert_and_query_asset(self, sync_engine):
        Base.metadata.create_all(sync_engine)
        with Session(sync_engine) as session:
            asset = Asset(
                ticker="AAPL", name="Apple Inc", sector="Information Technology"
            )
            session.add(asset)
            session.commit()
            result = session.execute(select(Asset).where(Asset.ticker == "AAPL"))
            found = result.scalar_one()
            assert found.name == "Apple Inc"

    def test_insert_score_with_asset(self, sync_engine):
        Base.metadata.create_all(sync_engine)
        with Session(sync_engine) as session:
            asset = Asset(
                ticker="NVDA", name="NVIDIA", sector="Information Technology"
            )
            session.add(asset)
            session.flush()
            score = Score(
                asset_id=asset.id,
                composite_percentile=99.5,
                conviction_level="exceptional",
                signal="buy",
            )
            session.add(score)
            session.commit()
            assert score.asset_id == asset.id
