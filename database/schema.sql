-- ============================================
-- AI Trading App - PostgreSQL Schema
-- Run this manually or let SQLAlchemy auto-create via init_db()
-- ============================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id                      SERIAL PRIMARY KEY,
    email                   VARCHAR(255) UNIQUE NOT NULL,
    username                VARCHAR(100) UNIQUE NOT NULL,
    hashed_password         VARCHAR(255) NOT NULL,
    is_active               BOOLEAN DEFAULT TRUE,
    is_admin                BOOLEAN DEFAULT FALSE,
    angel_one_api_key       TEXT,
    angel_one_client_id     VARCHAR(50),
    angel_one_password      TEXT,
    angel_one_totp_secret   TEXT,
    angel_one_jwt_token     TEXT,
    angel_one_refresh_token TEXT,
    angel_one_token_expiry  TIMESTAMP,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- Portfolios
CREATE TABLE IF NOT EXISTS portfolios (
    id                  SERIAL PRIMARY KEY,
    user_id             INT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_investment    FLOAT DEFAULT 0,
    current_value       FLOAT DEFAULT 0,
    available_margin    FLOAT DEFAULT 0,
    used_margin         FLOAT DEFAULT 0,
    total_pnl           FLOAT DEFAULT 0,
    realized_pnl        FLOAT DEFAULT 0,
    unrealized_pnl      FLOAT DEFAULT 0,
    today_pnl           FLOAT DEFAULT 0,
    last_synced         TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- Holdings (delivery stocks)
CREATE TABLE IF NOT EXISTS holdings (
    id              SERIAL PRIMARY KEY,
    portfolio_id    INT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol          VARCHAR(50) NOT NULL,
    exchange        VARCHAR(10) DEFAULT 'NSE',
    isin            VARCHAR(20),
    quantity        INT DEFAULT 0,
    avg_buy_price   FLOAT DEFAULT 0,
    current_price   FLOAT DEFAULT 0,
    current_value   FLOAT DEFAULT 0,
    pnl             FLOAT DEFAULT 0,
    pnl_percent     FLOAT DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);

-- Open positions (intraday/F&O)
CREATE TABLE IF NOT EXISTS positions (
    id              SERIAL PRIMARY KEY,
    portfolio_id    INT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol          VARCHAR(50) NOT NULL,
    exchange        VARCHAR(10) DEFAULT 'NSE',
    product_type    VARCHAR(20) DEFAULT 'INTRADAY',
    quantity        INT DEFAULT 0,
    buy_qty         INT DEFAULT 0,
    sell_qty        INT DEFAULT 0,
    avg_buy_price   FLOAT DEFAULT 0,
    avg_sell_price  FLOAT DEFAULT 0,
    current_price   FLOAT DEFAULT 0,
    pnl             FLOAT DEFAULT 0,
    unrealized_pnl  FLOAT DEFAULT 0,
    is_open         BOOLEAN DEFAULT TRUE,
    strike_price    FLOAT,
    option_type     VARCHAR(5),
    expiry_date     VARCHAR(20),
    updated_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_positions_portfolio ON positions(portfolio_id);

-- AI Signals
CREATE TABLE IF NOT EXISTS signals (
    id                  SERIAL PRIMARY KEY,
    symbol              VARCHAR(50) NOT NULL,
    exchange            VARCHAR(10) DEFAULT 'NSE',
    signal_type         VARCHAR(10) NOT NULL,       -- BUY / SELL / HOLD
    strength            VARCHAR(20) DEFAULT 'MODERATE',
    confidence          FLOAT NOT NULL,
    entry_price         FLOAT NOT NULL,
    stop_loss           FLOAT NOT NULL,
    target_1            FLOAT NOT NULL,
    target_2            FLOAT,
    target_3            FLOAT,
    risk_reward_ratio   FLOAT NOT NULL,
    rsi                 FLOAT,
    macd                FLOAT,
    macd_signal         FLOAT,
    vwap                FLOAT,
    ema_9               FLOAT,
    ema_21              FLOAT,
    ema_50              FLOAT,
    volume_spike        BOOLEAN DEFAULT FALSE,
    reasons             JSONB,
    pattern_detected    VARCHAR(100),
    trend               VARCHAR(20),
    is_active           BOOLEAN DEFAULT TRUE,
    is_triggered        BOOLEAN DEFAULT FALSE,
    is_hit_target       BOOLEAN DEFAULT FALSE,
    is_hit_stoploss     BOOLEAN DEFAULT FALSE,
    actual_pnl          FLOAT,
    created_at          TIMESTAMP DEFAULT NOW(),
    expires_at          TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type);

-- Trades / Orders
CREATE TABLE IF NOT EXISTS trades (
    id                      SERIAL PRIMARY KEY,
    user_id                 INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol                  VARCHAR(50) NOT NULL,
    exchange                VARCHAR(10) DEFAULT 'NSE',
    order_type              VARCHAR(30) DEFAULT 'MARKET',
    order_side              VARCHAR(10) NOT NULL,
    product_type            VARCHAR(20) DEFAULT 'INTRADAY',
    quantity                INT NOT NULL,
    price                   FLOAT DEFAULT 0,
    trigger_price           FLOAT DEFAULT 0,
    status                  VARCHAR(20) DEFAULT 'PENDING',
    angel_one_order_id      VARCHAR(100),
    executed_price          FLOAT DEFAULT 0,
    executed_qty            INT DEFAULT 0,
    pnl                     FLOAT DEFAULT 0,
    charges                 FLOAT DEFAULT 0,
    signal_id               INT REFERENCES signals(id),
    is_algo_order           BOOLEAN DEFAULT FALSE,
    notes                   TEXT,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at);

-- Default admin user (password: admin123 — change immediately)
-- bcrypt hash of 'admin123'
INSERT INTO users (email, username, hashed_password, is_admin) VALUES
(
    'admin@trading.app',
    'admin',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    TRUE
)
ON CONFLICT (email) DO NOTHING;
