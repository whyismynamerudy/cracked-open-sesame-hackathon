from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.agents.router import router as agents_router
from app.sessions.router import router as sessions_router
from app.core.config import Settings
from app.sessions import cleanup_sessions

description = """
```
_______.  ______    __          ___      .______       __       _______.
/       | /  __  \  |  |        /   \     |   _  \     |  |     /       |
|   (----`|  |  |  | |  |       /  ^  \    |  |_)  |    |  |    |   (----`
\   \    |  |  |  | |  |      /  /_\  \   |      /     |  |     \   \    
.----)   |   |  `--'  | |  `----./  _____  \  |  |\  \----.|  | .----)   |   
|_______/     \______/  |_______/__/     \__\ | _| `._____||__| |_______/    
```

Solaris Browse API

An API for managing browser automation sessions with multiple approaches:
    1. Direct browser control with Browserbase and Claude analysis
    2. AI agent-based automation with LangChain for complex tasks
    
    Supports parallel browser sessions, navigation, and AI-powered page analysis.
"""

settings = Settings()

app = FastAPI(
    title="Solaris Browse",
    description=description,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions_router)
app.include_router(agents_router)

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
