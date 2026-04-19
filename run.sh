#!/bin/bash
echo "🚀 Starting Arc Auditing Software..."

# Start Backend
echo "Starting FastAPI Backend on Port 8001..."
source venv/bin/activate
PYTHONPATH=. uvicorn backend.main:app --port 8001 --reload &
BACKEND_PID=$!

# Start Frontend
echo "Starting Vue 3 Frontend on Port 3001..."
cd frontend
npx http-server -p 3001 &
FRONTEND_PID=$!

echo "✅ Both servers are running!"
echo "➡️ Frontend Interface: http://localhost:3001"
echo "➡️ Backend API Docs:   http://localhost:8001/docs"
echo "Press Ctrl+C to stop both servers."

# Wait for process to exit
wait $BACKEND_PID $FRONTEND_PID
