#!/bin/bash

# Trading Bot Development Orchestrator
# This script starts both backend and frontend services

set -e

echo "🚀 Starting Trading Bot Development Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "backend/sma_cross_bot.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    print_status "Cleaning up background processes..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Step 1: Activate backend environment
print_status "Setting up backend environment..."
cd backend

if [ ! -d ".venv" ]; then
    print_warning "Backend virtual environment not found. Creating..."
    python -m venv .venv
fi

source .venv/bin/activate

# Install backend dependencies
print_status "Installing backend dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning "Backend .env file not found. Creating from sample..."
    if [ -f ".env.sample" ]; then
        cp .env.sample .env
        print_warning "Please update backend/.env with your actual API keys"
    else
        print_error "No .env.sample found. Please create backend/.env manually"
        exit 1
    fi
fi

# Step 2: Install frontend dependencies
print_status "Setting up frontend environment..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    print_status "Installing frontend dependencies..."
    npm install
fi

# Step 3: Start backend (in background)
print_status "Starting backend server..."
cd ../backend
python run_tests_then_bot.py &
BACKEND_PID=$!
print_success "Backend started with PID: $BACKEND_PID"

# Wait a moment for backend to initialize
sleep 3

# Step 4: Start frontend (in background)
print_status "Starting frontend development server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
print_success "Frontend started with PID: $FRONTEND_PID"

# Wait a moment for frontend to initialize
sleep 3

# Step 5: Display status and URLs
echo ""
echo "=========================================="
print_success "🎉 Development environment is ready!"
echo "=========================================="
echo ""
echo "📊 Services:"
echo "  • Frontend: http://localhost:3000"
echo "  • Backend API: http://localhost:8000"
echo "  • WebSocket: ws://localhost:8000/ws"
echo "  • Metrics: http://localhost:8000/metrics"
echo ""
echo "🔄 Processes:"
echo "  • Backend PID: $BACKEND_PID"
echo "  • Frontend PID: $FRONTEND_PID"
echo ""
echo "📁 Logs:"
echo "  • Backend logs: Check terminal output"
echo "  • Test results: backend/logs/test_suite_summary.csv"
echo "  • Test chart: backend/logs/test_suite_passrate.png"
echo ""
echo "🛑 To stop: Press Ctrl+C"
echo ""

# Keep script running and monitor processes
while true; do
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend process died unexpectedly"
        cleanup
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend process died unexpectedly"
        cleanup
    fi
    
    sleep 5
done 