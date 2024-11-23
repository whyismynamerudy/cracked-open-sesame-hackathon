from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import Settings
from app.sessions.router import router as sessions_router, cleanup_sessions

settings = Settings()

app = FastAPI(
    title="Solaris Browse API",
    description="""
    An API for managing browser automation sessions with Browserbase and Claude analysis.
    Allows creation of parallel browser sessions, navigation, and AI-powered page analysis.
    """,
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include session routes
app.include_router(sessions_router)

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "healthy", "version": "1.0.0"}

@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up all active sessions when shutting down
    """
    cleanup_sessions()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    )
