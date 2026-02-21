"""Tests for database models using SQLite in-memory."""

from __future__ import annotations

import pytest
from margin_api.db.base import Base
from margin_api.db.models import (
    ApiKey,
    Asset,
    BacktestResult,
    BacktestRun,
    FinancialData,
    IngestionRun,
    MetricsDerived,
    PriceIntraday,
    Recommendation,
    Score,
    User,
)
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
        assert "password_hash" in columns

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

    def test_no_unique_constraint_allows_rotation_overlap(self):
        """UniqueConstraint was removed to allow multiple keys per provider during rotation."""
        constraints = [
            c.name
            for c in ApiKey.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_user_provider" not in constraints


class TestFinancialDataModel:
    def test_financial_data_has_required_columns(self):
        """FinancialData model has all expected columns."""
        from sqlalchemy import inspect

        mapper = inspect(FinancialData)
        column_names = {c.key for c in mapper.column_attrs}
        expected = {
            "id",
            "asset_id",
            "period_end",
            "filing_date",
            "income_statement",
            "balance_sheet",
            "cash_flow",
            "price_history",
            "earnings_data",
            "source",
            "fetched_at",
        }
        assert expected.issubset(column_names)

    def test_financial_data_tablename(self):
        assert FinancialData.__tablename__ == "financial_data"


class TestScoreDetailColumn:
    def test_score_has_score_detail_column(self):
        """Score model has the score_detail JSONB column."""
        from sqlalchemy import inspect

        mapper = inspect(Score)
        column_names = {c.key for c in mapper.column_attrs}
        assert "score_detail" in column_names


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
        assert "prices_intraday" in table_names
        assert "metrics_derived" in table_names
        assert "backtest_runs" in table_names
        assert "backtest_results" in table_names

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


class TestPriceIntradayModel:
    def test_table_name(self):
        assert PriceIntraday.__tablename__ == "prices_intraday"

    def test_columns(self):
        columns = {c.name for c in PriceIntraday.__table__.columns}
        expected = {"time", "ticker", "open", "high", "low", "close", "volume", "source"}
        assert expected.issubset(columns)

    def test_composite_primary_key(self):
        pk_cols = {c.name for c in PriceIntraday.__table__.primary_key.columns}
        assert pk_cols == {"time", "ticker"}

    def test_open_not_nullable(self):
        col = PriceIntraday.__table__.columns["open"]
        assert col.nullable is False

    def test_volume_nullable(self):
        col = PriceIntraday.__table__.columns["volume"]
        assert col.nullable is True


class TestMetricsDerivedModel:
    def test_table_name(self):
        assert MetricsDerived.__tablename__ == "metrics_derived"

    def test_columns(self):
        columns = {c.name for c in MetricsDerived.__table__.columns}
        expected = {
            "id", "asset_id", "as_of_date",
            "roe", "roic", "gross_margin", "debt_to_equity",
            "pe_ratio", "pb_ratio", "ev_ebitda", "fcf_yield",
            "return_1m", "return_3m", "return_6m", "return_12m",
            "extra", "computed_at",
        }
        assert expected.issubset(columns)

    def test_unique_constraint(self):
        constraint_names = [
            c.name for c in MetricsDerived.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_metrics_asset_date" in constraint_names

    def test_asset_fk(self):
        col = MetricsDerived.__table__.columns["asset_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "assets.id"


class TestBacktestRunModel:
    def test_table_name(self):
        assert BacktestRun.__tablename__ == "backtest_runs"

    def test_columns(self):
        columns = {c.name for c in BacktestRun.__table__.columns}
        expected = {
            "id", "name", "universe_snapshot_id", "start_date", "end_date",
            "rebalance_frequency", "config", "config_hash", "status",
            "total_return", "annualized_return", "sharpe_ratio", "max_drawdown",
            "summary_stats", "started_at", "completed_at", "created_at",
        }
        assert expected.issubset(columns)

    def test_config_not_nullable(self):
        col = BacktestRun.__table__.columns["config"]
        assert col.nullable is False

    def test_config_hash_not_nullable(self):
        col = BacktestRun.__table__.columns["config_hash"]
        assert col.nullable is False

    def test_universe_snapshot_fk(self):
        col = BacktestRun.__table__.columns["universe_snapshot_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "universe_snapshots.id"


class TestBacktestResultModel:
    def test_table_name(self):
        assert BacktestResult.__tablename__ == "backtest_results"

    def test_columns(self):
        columns = {c.name for c in BacktestResult.__table__.columns}
        expected = {
            "id", "run_id", "asset_id", "as_of_date", "signal",
            "conviction_level", "composite_percentile",
            "entry_price", "exit_price", "position_return", "detail",
        }
        assert expected.issubset(columns)

    def test_signal_not_nullable(self):
        col = BacktestResult.__table__.columns["signal"]
        assert col.nullable is False

    def test_composite_percentile_not_nullable(self):
        col = BacktestResult.__table__.columns["composite_percentile"]
        assert col.nullable is False

    def test_cascade_delete(self):
        col = BacktestResult.__table__.columns["run_id"]
        fks = list(col.foreign_keys)
        assert fks[0].ondelete == "CASCADE"

    def test_unique_constraint(self):
        constraint_names = [
            c.name for c in BacktestResult.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_backtest_result" in constraint_names

    def test_has_relationship_to_run(self):
        assert hasattr(BacktestResult, "run")


class TestScoreUniverseLink:
    def test_score_has_universe_snapshot_id(self):
        columns = {c.name for c in Score.__table__.columns}
        assert "universe_snapshot_id" in columns

    def test_universe_snapshot_id_nullable(self):
        col = Score.__table__.columns["universe_snapshot_id"]
        assert col.nullable is True

    def test_universe_snapshot_id_fk(self):
        col = Score.__table__.columns["universe_snapshot_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "universe_snapshots.id"


class TestIngestionRunDataTypes:
    def test_ingestion_run_has_data_types(self):
        columns = {c.name for c in IngestionRun.__table__.columns}
        assert "data_types" in columns
