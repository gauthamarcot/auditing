# Arc Auditing Software

A standalone, fully-featured AI Auditing Dashboard. This software utilizes an intelligent frontend UI connected to an async FastAPI backend with an integrated SQLite database for true multi-tenancy and ledger administration.

## Prerequisites
- Python 3.9+
- Node.js (for `npx http-server` serving)

## Easy Run
We have provided a unified runner script that spins up the backend virtual environment and the frontend HTTP server concurrently:

```bash
chmod +x run.sh
./run.sh
```

## Manual Setup

### 1. Backend Server
The backend powers the Virtual CA multi-tenant database, Tally mocking logic, and the core analytical algorithms.

```bash
# Activate the Python Virtual Environment
source venv/bin/activate

# Install any missing requirements
pip install -r backend/requirements.txt

# Run the Uvicorn web server
PYTHONPATH=. uvicorn backend.main:app --port 8001 --reload
```

The server will be live at `http://127.0.0.1:8001`. You can access the API Swagger playground at `http://127.0.0.1:8001/docs`.

### 2. Frontend Interface
The frontend consists of vanilla HTML/CSS connected to Vue 3 (via CDN).

```bash
cd frontend
npx http-server -p 3001
```

Access the master UI Dashboard at **`http://localhost:3001`**.
