from app.core.config import Settings
from app.sessions.router import cleanup_sessions, create_session
from app.sessions.router import router as sessions_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

def create_app():
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

    # Root endpoint for health check
    @app.get("/")
    async def root():
        return {"status": "healthy", "version": "1.0.0"}
# Add new endpoint
@app.post("/execute")
async def execute():
    """
    Execute a browser automation task and return the session ID
    """
    # Call the sessions/create endpoint
    session_data = await create_session()
    
    # Navigate to the session
    navigation_response = await navigate(
        navigation=NavigationRequest(url=request.url, intent=request.intent),
        session_id=session_data["session_id"]
    )
    
    # Extract session ID and debugging URL from response
    session_id = session_data["session_id"]
    debugging_url = session_data["debugger_url"]
    status = session_data["status"]
    title = navigation_response["title"]

    return {
    "sessionId": session_id,
    "debuggingUrl": debugging_url,
    "status": status,
    "title": title
    }

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=["app"],
        workers=1  # Use single worker to avoid multiprocessing issues
    )
