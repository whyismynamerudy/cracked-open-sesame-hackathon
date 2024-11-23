from app.core.config import Settings
from app.sessions.router import cleanup_sessions
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
    # You'll need to implement the logic to create/get a session
    session_id = "your-session-id-logic-here"  # Replace with actual session creation
    # Call the agents/execute endpoint
    response = await app.url_for("/agents/execute")(
        request=ExecuteRequest(
            url=request.body.url,
            intent=request.body.intent,
            context=request.body.context
        )
    )
    # Extract session ID and debugging URL from response
    session_id = response["data"]["execution_results"]["session_id"]
    debugging_url = response["data"]["execution_results"]["debugger_url"]
    status = response["data"]["status"]
    
    return {
        "sessionId": session_id,
        "debuggingUrl": debugging_url,
        "status": status
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
