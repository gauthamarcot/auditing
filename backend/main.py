from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import documents, analytics

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auditing and Taxation App API")

# Configure CORS for Vue Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"], # Fix for wildcard CORS rejection with credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(analytics.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Auditing and Taxation API"}
