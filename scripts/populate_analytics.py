import asyncio
import os
import sys
from datetime import date, timedelta, datetime
from decimal import Decimal
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import DATE # For casting DateTime to Date in SQLite group by

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.db.session import get_async_engine, get_db_session_context
from ai_trader.models import Trade, DailyProfit, MonthlySummary, User, Strategy, TradeType

async def calculate_and_store_daily_profits(db: AsyncSession, specific_date: date = None):
    """
    Calculates profit from trades for a specific day (or yesterday if not specified)
    and stores it in the DailyProfit table.
    This assumes 'profit' is derived from trades. A simple PnL could be (sell_price - buy_price) * quantity.
    For this example, let's assume a simplified profit calculation: sum of (price * quantity) for SELL trades
    minus sum of (price * quantity) for BUY trades. This is a VERY naive approach to PnL and would
    need proper accounting for actual cost basis, fees, etc., in a real system.
    We will sum (price * quantity) for all trades for simplicity for now as 'turnover' or 'value'.
    A true profit calculation needs pairing of buy/sell trades or marking-to-market.

    For this example, we'll define "profit" for a day as:
    Sum of (price * quantity) for SELL trades - Sum of (price * quantity) for BUY trades.
    This is a basic cash flow view, not a true PnL of asset appreciation.
    """
    if specific_date is None:
        specific_date = date.today() - timedelta(days=1) # Default to yesterday

    print(f"Calculating daily profits for: {specific_date}")

    # Delete existing entries for this date to avoid duplicates if re-run
    await db.execute(delete(DailyProfit).where(DailyProfit.profit_date == specific_date))

    # Group by user_id, strategy_id (nullable), and the date part of trade.executed_at
    # Note: Grouping by executed_at requires casting to date for SQLite.
    # For PostgreSQL, func.date(Trade.executed_at) would work.
    # For SQLite, strftime('%Y-%m-%d', Trade.executed_at) is common.
    # SQLAlchemy's func.cast(Trade.executed_at, DATE) might work for some backends.
    # Let's use strftime for SQLite compatibility here.

    # This query is complex due to needing to aggregate by user and potentially strategy.
    # A simpler version would be system-wide profit.
    # For now, let's focus on per-user profit. Strategy can be added later.

    # Sum of SELLs
    sell_trades_stmt = (
        select(
            Trade.user_id,
            # Trade.strategy_id, # Add if grouping by strategy
            func.sum(Trade.price * Trade.quantity).label("total_sell_value"),
            func.count(Trade.id).label("sell_trade_count"),
        )
        .where(func.strftime('%Y-%m-%d', Trade.executed_at) == specific_date.strftime('%Y-%m-%d'))
        .where(Trade.trade_type == TradeType.SELL)
        .group_by(Trade.user_id) # Add Trade.strategy_id if grouping by strategy
    )
    sell_results = (await db.execute(sell_trades_stmt)).fetchall()

    # Sum of BUYs
    buy_trades_stmt = (
        select(
            Trade.user_id,
            # Trade.strategy_id, # Add if grouping by strategy
            func.sum(Trade.price * Trade.quantity).label("total_buy_value"),
            func.count(Trade.id).label("buy_trade_count")
        )
        .where(func.strftime('%Y-%m-%d', Trade.executed_at) == specific_date.strftime('%Y-%m-%d'))
        .where(Trade.trade_type == TradeType.BUY)
        .group_by(Trade.user_id) # Add Trade.strategy_id if grouping by strategy
    )
    buy_results = (await db.execute(buy_trades_stmt)).fetchall()

    daily_profits_data = {} # Key: (user_id), Value: {profit, trades, volume}

    for row in sell_results:
        key = (row.user_id,)
        if key not in daily_profits_data:
            daily_profits_data[key] = {"profit": Decimal(0), "trades": 0, "volume": Decimal(0)}
        daily_profits_data[key]["profit"] += Decimal(row.total_sell_value or 0)
        daily_profits_data[key]["trades"] += row.sell_trade_count or 0
        daily_profits_data[key]["volume"] += Decimal(row.total_sell_value or 0)


    for row in buy_results:
        key = (row.user_id,)
        if key not in daily_profits_data:
            daily_profits_data[key] = {"profit": Decimal(0), "trades": 0, "volume": Decimal(0)}
        # Subtract buy value for profit calculation
        daily_profits_data[key]["profit"] -= Decimal(row.total_buy_value or 0)
        daily_profits_data[key]["trades"] += row.buy_trade_count or 0
        daily_profits_data[key]["volume"] += Decimal(row.total_buy_value or 0) # Volume includes both

    # Store results
    for key, data in daily_profits_data.items():
        user_id = key[0]
        # strategy_id = key[1] # if strategy is part of key
        daily_profit_entry = DailyProfit(
            profit_date=specific_date,
            user_id=user_id,
            # strategy_id=strategy_id, # if used
            total_profit=data["profit"],
            total_trades=data["trades"],
            total_volume=data["volume"]
        )
        db.add(daily_profit_entry)
        print(f"  Stored daily profit for user {user_id} on {specific_date}: Profit={data['profit']}, Trades={data['trades']}")

    await db.commit()
    print(f"Daily profits calculation complete for {specific_date}.")


async def calculate_and_store_monthly_summaries(db: AsyncSession, year: int = None, month: int = None):
    """
    Calculates summaries from DailyProfit table for a specific month (or previous month if not specified)
    and stores it in the MonthlySummary table.
    """
    if year is None or month is None:
        today = date.today()
        first_day_current_month = today.replace(day=1)
        last_day_previous_month = first_day_current_month - timedelta(days=1)
        year = last_day_previous_month.year
        month = last_day_previous_month.month

    month_start_date = date(year, month, 1)
    print(f"Calculating monthly summary for: {year}-{month:02d}")

    # Delete existing entries for this month to avoid duplicates
    await db.execute(delete(MonthlySummary).where(MonthlySummary.month_year == month_start_date))

    # Aggregate from DailyProfit table
    stmt = (
        select(
            DailyProfit.user_id,
            # DailyProfit.strategy_id, # If daily profits are by strategy
            func.sum(DailyProfit.total_profit).label("monthly_profit"),
            func.sum(DailyProfit.total_trades).label("monthly_trades"),
            func.sum(DailyProfit.total_volume).label("monthly_volume")
        )
        .where(func.strftime('%Y-%m', DailyProfit.profit_date) == month_start_date.strftime('%Y-%m'))
        .group_by(DailyProfit.user_id) # Add DailyProfit.strategy_id if used
    )

    results = (await db.execute(stmt)).fetchall()

    for row in results:
        monthly_summary_entry = MonthlySummary(
            month_year=month_start_date,
            user_id=row.user_id,
            # strategy_id=row.strategy_id, # if used
            total_profit=Decimal(row.monthly_profit or 0),
            total_trades=row.monthly_trades or 0,
            total_volume=Decimal(row.monthly_volume or 0)
        )
        db.add(monthly_summary_entry)
        print(f"  Stored monthly summary for user {row.user_id} for {year}-{month:02d}: Profit={row.monthly_profit}, Trades={row.monthly_trades}")

    await db.commit()
    print(f"Monthly summary calculation complete for {year}-{month:02d}.")


async def main():
    engine = get_async_engine()
    # Optionally create tables if they don't exist - useful for testing this script standalone
    # async with engine.begin() as conn:
    #     from ai_trader.db.base import Base
    #     await conn.run_sync(Base.metadata.create_all)

    async with get_db_session_context() as db:
        # Example: Calculate for yesterday and previous month
        # In a cron job, you'd likely calculate for 'today - 1 day' and check if it's start of month
        # to trigger monthly calculation.

        yesterday = date.today() - timedelta(days=1)
        await calculate_and_store_daily_profits(db, specific_date=yesterday)

        # For monthly, calculate for the month of 'yesterday'
        await calculate_and_store_monthly_summaries(db, year=yesterday.year, month=yesterday.month)

if __name__ == "__main__":
    print("Running populate_analytics.py script...")
    asyncio.run(main())
    print("Analytics population script finished.")
