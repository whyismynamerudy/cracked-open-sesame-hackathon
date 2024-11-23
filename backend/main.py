from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import Settings

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Add any async resources here (database, cache, etc.)
    print("Starting up...")
    yield
    # Shutdown: Clean up any resources
    print("Shutting down...")

app = FastAPI(
    title="AI Agent Backend",
    description="API for AI Agents with Browser Automation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "healthy", "version": "1.0.0"}