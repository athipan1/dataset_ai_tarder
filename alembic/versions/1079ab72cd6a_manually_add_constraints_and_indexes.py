"""Manually add constraints and indexes

Revision ID: 1079ab72cd6a
Revises: 397302ad8134
Create Date: 2025-07-05 19:56:18.584681

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1079ab72cd6a"
down_revision: Union[str, Sequence[str], None] = "397302ad8134"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Foreign Key Constraints
    # Need to drop existing ones if their ondelete behavior changes or if names conflict.
    # SQLite requires batch mode for most of these operations.

    # Strategy.user_id
    with op.batch_alter_table("strategies", schema=None) as batch_op:
        # We will rely on batch mode to recreate the table with new FKs,
        # so explicit dropping of old FKs is removed to avoid naming issues.
        batch_op.create_foreign_key(
            "fk_strategy_user_cascade", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        # Unique constraint for Strategy: user_id, name
        batch_op.create_unique_constraint("uq_user_strategy_name", ["user_id", "name"])

    # Order.user_id, Order.asset_id, Order.strategy_id
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_order_user_set_null", "users", ["user_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            "fk_order_asset_cascade", "assets", ["asset_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key(
            "fk_order_strategy_set_null",
            "strategies",
            ["strategy_id"],
            ["id"],
            ondelete="SET NULL",
        )
        # signal_id FK in orders is fine as is, no ondelete specified in plan for it.

    # Trade.user_id, Trade.order_id
    with op.batch_alter_table("trades", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_trade_user_cascade", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key(
            "fk_trade_order_cascade", "orders", ["order_id"], ["id"], ondelete="CASCADE"
        )

    # TradeAnalytics.user_id, TradeAnalytics.strategy_id
    with op.batch_alter_table("trade_analytics", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_tradeanalytics_user_cascade",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_tradeanalytics_strategy_cascade",
            "strategies",
            ["strategy_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # UserBehaviorLog.user_id
    with op.batch_alter_table("user_behavior_logs", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_userbehaviorlog_user_cascade",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Signal.asset_id, Signal.strategy_id
    with op.batch_alter_table("signals", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_signal_asset_cascade",
            "assets",
            ["asset_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_signal_strategy_cascade",
            "strategies",
            ["strategy_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # PriceData.asset_id
    with op.batch_alter_table("price_data", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_pricedata_asset_cascade",
            "assets",
            ["asset_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # BacktestResult.strategy_id
    with op.batch_alter_table("backtest_results", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_backtestresult_strategy_cascade",
            "strategies",
            ["strategy_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Composite Indexes
    op.create_index(
        "ix_order_status_user_created",
        "orders",
        ["status", "user_id", "created_at"],
        unique=False,
    )
    # The other index on orders idx_order_asset_strategy_created should already exist or be handled by SQLAlchemy's __table_args__

    # Drop old index if it exists, then create new one for trades
    try:
        op.drop_index("ix_trade_user_id_symbol_timestamp", table_name="trades")
    except sa.exc.OperationalError as e:
        print(
            f"Info: Could not drop index 'ix_trade_user_id_symbol_timestamp' (may not exist): {e}"
        )
    except Exception as e:
        print(
            f"Warning: An unexpected error occurred while dropping index 'ix_trade_user_id_symbol_timestamp': {e}"
        )
    op.create_index(
        "ix_trade_user_symbol_timestamp_type",
        "trades",
        ["user_id", "symbol", "timestamp", "trade_type"],
        unique=False,
    )

    # Partial Index (PostgreSQL specific)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "idx_open_orders_user_id",
            "orders",
            ["user_id"],
            unique=False,
            postgresql_where=sa.text("status = 'OPEN'"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Partial Index (PostgreSQL specific)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(
            "idx_open_orders_user_id",
            table_name="orders",
            postgresql_where=sa.text("status = 'OPEN'"),
        )

    # Composite Indexes
    op.drop_index("ix_order_status_user_created", table_name="orders")
    op.drop_index("ix_trade_user_symbol_timestamp_type", table_name="trades")
    # Recreate old index for trades if needed (assuming it was ix_trade_user_id_symbol_timestamp)
    op.create_index(
        "ix_trade_user_id_symbol_timestamp",
        "trades",
        ["user_id", "symbol", "timestamp"],
        unique=False,
    )

    # Foreign Key and Unique Constraints (revert to old or remove)
    # For simplicity, we'll mostly drop the specific named constraints added in upgrade.
    # Reverting ondelete behavior accurately would require knowing the exact previous state.

    with op.batch_alter_table("strategies", schema=None) as batch_op:
        batch_op.drop_constraint("fk_strategy_user_cascade", type_="foreignkey")
        # Recreate old FK if known, e.g., op.create_foreign_key('strategies_user_id_fkey', 'users', ['user_id'], ['id'])
        batch_op.drop_constraint("uq_user_strategy_name", type_="unique")

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_constraint("fk_order_user_set_null", type_="foreignkey")
        batch_op.drop_constraint("fk_order_asset_cascade", type_="foreignkey")
        batch_op.drop_constraint("fk_order_strategy_set_null", type_="foreignkey")
        # Recreate old FKs if known

    with op.batch_alter_table("trades", schema=None) as batch_op:
        batch_op.drop_constraint("fk_trade_user_cascade", type_="foreignkey")
        batch_op.drop_constraint("fk_trade_order_cascade", type_="foreignkey")

    with op.batch_alter_table("trade_analytics", schema=None) as batch_op:
        batch_op.drop_constraint("fk_tradeanalytics_user_cascade", type_="foreignkey")
        batch_op.drop_constraint(
            "fk_tradeanalytics_strategy_cascade", type_="foreignkey"
        )

    with op.batch_alter_table("user_behavior_logs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_userbehaviorlog_user_cascade", type_="foreignkey")

    with op.batch_alter_table("signals", schema=None) as batch_op:
        batch_op.drop_constraint("fk_signal_asset_cascade", type_="foreignkey")
        batch_op.drop_constraint("fk_signal_strategy_cascade", type_="foreignkey")

    with op.batch_alter_table("price_data", schema=None) as batch_op:
        batch_op.drop_constraint("fk_pricedata_asset_cascade", type_="foreignkey")

    with op.batch_alter_table("backtest_results", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_backtestresult_strategy_cascade", type_="foreignkey"
        )
