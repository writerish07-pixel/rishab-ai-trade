# AI Trading App — Setup Guide

## System Requirements
- Python 3.11+
- Node.js 20+
- Docker + Docker Compose
- PostgreSQL 15+ (via Docker)
- Redis 7+ (via Docker)

---

## Quick Start (Docker — Recommended)

```bash
# 1. Clone / open project
cd trading-app

# 2. Set up credentials
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

# 3. Launch everything
./start.sh docker

# OR
docker-compose up --build
```

Open: http://localhost:3000

---

## Local Development (Without Docker)

```bash
./start.sh local
```

Or manually:

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env

# Start Docker infra only
docker-compose up -d postgres redis

# Run backend
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Environment Variables (backend/.env)

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | JWT secret — use 32+ random chars | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `ANGEL_ONE_API_KEY` | From smartapi.angelbroking.com | For live trading |
| `ANGEL_ONE_CLIENT_ID` | Your Angel One ID | For live trading |
| `ANGEL_ONE_PASSWORD` | Your trading PIN | For live trading |
| `ANGEL_ONE_TOTP_SECRET` | Base32 TOTP from authenticator | For live trading |
| `POLYGON_API_KEY` | From polygon.io | Optional |
| `ALPACA_API_KEY` | From alpaca.markets | Optional |

---

## Angel One SmartAPI Setup

1. Register at https://smartapi.angelbroking.com/
2. Create a new app → get API Key
3. Your Client ID = your Angel One login ID
4. Password = your 4/6 digit trading PIN
5. TOTP Secret = shown during authenticator setup (scan QR manually to get Base32 key)
6. In the app: Settings → Connect Angel One → enter credentials

---

## VS Code Setup

Open `trading-app.code-workspace` in VS Code for the full workspace experience:
- Multi-root workspace (backend + frontend)
- Debug configurations
- Task shortcuts (F5 to start backend debugger)
- Recommended extensions auto-prompt

---

## API Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

---

## Default Login

```
Email:    admin@trading.app
Password: admin123
```
**Change this in production!**

---

## Architecture

```
trading-app/
├── backend/               # Python FastAPI
│   ├── app/
│   │   ├── core/          # Config, DB, Redis, Security
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── routers/       # API endpoints
│   │   ├── services/      # Angel One, Market Data, etc.
│   │   └── ai/            # Signal engine, Indicators, Patterns
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/              # Next.js + TypeScript
│   ├── src/
│   │   ├── app/           # Pages (dashboard, portfolio, signals...)
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks (WebSocket, Market Data)
│   │   ├── store/         # Redux slices
│   │   ├── services/      # API client, WebSocket
│   │   └── types/         # TypeScript types
│   └── Dockerfile
├── database/
│   └── schema.sql         # PostgreSQL schema
├── docker-compose.yml
└── start.sh
```

---

## Key Features

### AI Signal Engine
- Scans Nifty 50 stocks continuously
- Multi-indicator confirmation (RSI + MACD + EMA + VWAP + ADX + Supertrend)
- Pattern detection (Breakout, Engulfing, Hammer, VWAP bounce, etc.)
- Institutional activity tracking (NSE bulk/block deals + delivery %)
- Target: 65-70%+ signal confidence
- Entry, SL, T1/T2/T3 with ATR-based level calculation

### Angel One Integration
- Login with TOTP (2FA) automatically
- Real-time order placement (Market, Limit, SL, Bracket)
- Portfolio sync (Holdings, Positions, P&L)
- Order book, trade history, margin data
- WebSocket market feed (via SmartWebSocketV2)

### Market Data Sources (auto-failover)
1. Angel One SmartAPI (primary for Indian markets)
2. Polygon.io
3. Alpaca
4. yFinance (fallback — always available)

### WebSocket Live Feed
- Sub-second price updates via WebSocket
- Auto-reconnect with exponential backoff
- Symbol-based subscription management
- Signal alerts pushed in real-time

---

## Production Deployment Notes

1. Set `DEBUG=false` in backend/.env
2. Use a strong `SECRET_KEY` (run: `python -c "import secrets; print(secrets.token_hex(32))"`)
3. Encrypt Angel One credentials at rest (use HashiCorp Vault or AWS Secrets Manager)
4. Put Nginx in front of both services
5. Enable SSL/TLS
6. Set up proper CORS origins
7. Use read replicas for PostgreSQL at high scale

---

## Disclaimer

This software is for educational and personal use. Trading in equity markets carries risk. The AI signals are statistical in nature and do not guarantee profits. Always use proper risk management. The authors are not responsible for financial losses.
