#!/bin/bash
# ============================================
# AI Trading App - Quick Start Script
# ============================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║      AI Trading App - Startup Script     ║"
echo "║   NSE/BSE Intraday Trading Platform      ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# Check for .env
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}[Setup] Creating backend/.env from example...${NC}"
    cp backend/.env.example backend/.env
    echo -e "${RED}[!] Please edit backend/.env and add your credentials before trading!${NC}"
fi

if [ ! -f "frontend/.env.local" ]; then
    echo -e "${YELLOW}[Setup] Creating frontend/.env.local...${NC}"
    cp frontend/.env.example frontend/.env.local
fi

MODE=${1:-"docker"}

if [ "$MODE" = "docker" ]; then
    echo -e "${GREEN}[Docker] Starting all services with Docker Compose...${NC}"
    docker-compose up --build -d

    echo -e "${GREEN}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " Services Started:"
    echo "  Frontend:  http://localhost:3000"
    echo "  Backend:   http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/api/docs"
    echo "  Database:  localhost:5432"
    echo "  Redis:     localhost:6379"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${NC}"

elif [ "$MODE" = "local" ]; then
    echo -e "${GREEN}[Local] Starting services locally...${NC}"

    # Start PostgreSQL and Redis via Docker (infra only)
    echo "[1/4] Starting database and cache..."
    docker-compose up -d postgres redis
    sleep 3

    # Backend
    echo "[2/4] Setting up Python virtual environment..."
    cd backend
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt

    echo "[3/4] Starting FastAPI backend..."
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..

    # Frontend
    echo "[4/4] Starting Next.js frontend..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    echo -e "${GREEN}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " All services started (local mode):"
    echo "  Frontend:  http://localhost:3000"
    echo "  Backend:   http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/api/docs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " Press Ctrl+C to stop all services"
    echo -e "${NC}"

    # Wait and cleanup
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker-compose stop postgres redis" INT TERM
    wait
fi
