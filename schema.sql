-- SQL Schema for AI Trader Project
-- Dialect: Generic SQL (primarily for SQLite/PostgreSQL compatibility via SQLAlchemy)

-- Users Table (Existing)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assets Table (Existing)
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    asset_type VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_asset_symbol ON assets (symbol);

-- Strategies Table (Existing)
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    description TEXT,
    model_version VARCHAR,
    parameters TEXT, -- JSON
    api_key VARCHAR,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS idx_strategy_name ON strategies (name);

-- PriceData Table (Existing, added one index)
CREATE TABLE IF NOT EXISTS price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    "timestamp" TIMESTAMP NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    source VARCHAR NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES assets (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_asset_timestamp_source ON price_data (asset_id, "timestamp", source);
CREATE INDEX IF NOT EXISTS idx_pricedata_timestamp ON price_data ("timestamp"); -- New index

-- Signals Table (Existing)
-- Note: ENUM types are specific to DBMS (e.g., PostgreSQL). SQLAlchemy handles this.
-- For generic SQL, VARCHAR with CHECK constraint is an alternative.
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    strategy_id INTEGER NOT NULL,
    "timestamp" TIMESTAMP NOT NULL,
    signal_type VARCHAR NOT NULL, -- 'BUY', 'SELL', 'HOLD'
    confidence_score REAL,
    risk_score REAL,
    price_at_signal REAL,
    FOREIGN KEY (asset_id) REFERENCES assets (id),
    FOREIGN KEY (strategy_id) REFERENCES strategies (id)
);
CREATE INDEX IF NOT EXISTS idx_signal_asset_strategy_timestamp ON signals (asset_id, strategy_id, "timestamp");
CREATE INDEX IF NOT EXISTS idx_signal_type ON signals (signal_type);


-- Orders Table (Modified: added pnl)
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    asset_id INTEGER NOT NULL,
    strategy_id INTEGER,
    signal_id INTEGER,
    order_type VARCHAR NOT NULL, -- 'MARKET', 'LIMIT', 'STOP'
    order_side VARCHAR NOT NULL, -- 'BUY', 'SELL'
    status VARCHAR NOT NULL, -- 'PENDING', 'OPEN', 'FILLED', etc.
    quantity REAL NOT NULL,
    price REAL,
    filled_quantity REAL DEFAULT 0.0,
    average_fill_price REAL,
    commission REAL,
    exchange_order_id VARCHAR,
    is_simulated INTEGER DEFAULT 1 NOT NULL,
    pnl REAL, -- New field
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (asset_id) REFERENCES assets (id),
    FOREIGN KEY (strategy_id) REFERENCES strategies (id),
    FOREIGN KEY (signal_id) REFERENCES signals (id)
);
CREATE INDEX IF NOT EXISTS idx_order_asset_strategy_created ON orders (asset_id, strategy_id, created_at);
CREATE INDEX IF NOT EXISTS idx_order_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_order_exchange_id ON orders (exchange_order_id);

-- BacktestResults Table (Existing)
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    initial_capital REAL NOT NULL,
    final_capital REAL NOT NULL,
    total_profit REAL NOT NULL,
    total_trades INTEGER NOT NULL,
    winning_trades INTEGER NOT NULL,
    losing_trades INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    accuracy REAL,
    max_drawdown REAL NOT NULL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    parameters_used TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies (id)
);
CREATE INDEX IF NOT EXISTS idx_backtest_strategy_created ON backtest_results (strategy_id, created_at);

-- NEW TABLE: TechnicalIndicators
CREATE TABLE IF NOT EXISTS technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price_data_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL, -- For convenience
    "timestamp" TIMESTAMP NOT NULL,
    indicator_name VARCHAR NOT NULL,
    value REAL NOT NULL,
    parameters TEXT, -- JSON
    FOREIGN KEY (price_data_id) REFERENCES price_data (id),
    FOREIGN KEY (asset_id) REFERENCES assets (id)
);
CREATE INDEX IF NOT EXISTS idx_indicator_asset_timestamp_name ON technical_indicators (asset_id, "timestamp", indicator_name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_indicator_price_data_id_name ON technical_indicators (price_data_id, indicator_name);

-- NEW TABLE: TargetLabels
-- Note: ENUM types are specific to DBMS. SQLAlchemy handles this.
CREATE TABLE IF NOT EXISTS target_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    "timestamp" TIMESTAMP NOT NULL,
    label VARCHAR NOT NULL, -- 'BUY', 'SELL', 'HOLD'
    -- label_horizon VARCHAR,
    -- label_generation_method VARCHAR,
    FOREIGN KEY (asset_id) REFERENCES assets (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_label_asset_timestamp ON target_labels (asset_id, "timestamp");

-- For PostgreSQL, you might want to define ENUM types separately:
-- CREATE TYPE signal_type_enum AS ENUM ('BUY', 'SELL', 'HOLD');
-- CREATE TYPE order_type_enum AS ENUM ('MARKET', 'LIMIT', 'STOP');
-- CREATE TYPE order_side_enum AS ENUM ('BUY', 'SELL');
-- CREATE TYPE order_status_enum AS ENUM ('PENDING', 'OPEN', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED');
-- CREATE TYPE target_label_type_enum AS ENUM ('BUY', 'SELL', 'HOLD');
-- And then use these types in table definitions, e.g., signal_type signal_type_enum NOT NULL,

-- Note on JSON: SQLite stores JSON as TEXT. PostgreSQL has native JSON/JSONB types.
-- SQLAlchemy abstracts this.
-- Note on AUTOINCREMENT: Behavior differs slightly (e.g. `SERIAL` in PostgreSQL).
-- `Base.metadata.create_all(bind=engine)` in `models.py` handles dialect-specifics.
print("schema.sql file created. This is a general representation; SQLAlchemy in models.py will generate the precise DDL for the target database.")
