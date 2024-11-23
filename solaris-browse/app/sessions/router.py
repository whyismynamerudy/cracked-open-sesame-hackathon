from fastapi import APIRouter, BackgroundTasks, status, Path
from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import RemoteConnection
from browserbase import Browserbase
from typing import Dict
from anthropic import Anthropic
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/session",
    tags=["sessions"],
    responses={404: {"description": "Session not found"}}
)

# Environment variables
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Initialize clients
bb = Browserbase(api_key=BROWSERBASE_API_KEY)
anthropic = Anthropic(api_key=CLAUDE_API_KEY)

# Store active sessions
active_sessions = {}

class BrowserbaseConnection(RemoteConnection):
    """
    Manage a single session with Browserbase.
    """
    session_id: str

    def __init__(self, session_id: str, *args, **kwargs):  # type: ignore
        super().__init__(*args, **kwargs)  # type: ignore
        self.session_id = session_id

    def get_remote_connection_headers(  # type: ignore
        self, parsed_url: str, keep_alive: bool = False
    ) -> Dict[str, str]:
        headers = super().get_remote_connection_headers(parsed_url, keep_alive)  # type: ignore
        headers["x-bb-api-key"] = BROWSERBASE_API_KEY
        headers["session-id"] = self.session_id
        return headers  # type: ignore

class SessionResponse(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the browser session")
    status: str = Field(..., description="Status of the session creation request")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "status": "created"
            }
        }

class NavigationRequest(BaseModel):
    url: str = Field(..., description="URL to navigate to", example="https://example.com")

class NavigationResponse(BaseModel):
    url: str = Field(..., description="Current URL after navigation")
    title: str = Field(..., description="Page title")
    analysis: str = Field(..., description="AI analysis of the page content")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "title": "Example Domain",
                "analysis": "This appears to be a simple webpage with a heading and brief description..."
            }
        }

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Session not found"
            }
        }

def analyze_page_with_claude(html_content: str) -> str:
    """
    Send the HTML content to Claude and get analysis of what's happening on the page.
    """
    message = anthropic.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"Analyze this webpage and tell me what's happening on it. Here's the HTML:\n\n{html_content}"
        }]
    )
    return message.content

def create_browser_session():
    """
    Create a new browser session and return the session details
    """
    session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
    connection = BrowserbaseConnection(session.id, session.selenium_remote_url)
    driver = webdriver.Remote(
        command_executor=connection, options=webdriver.ChromeOptions()  # type: ignore
    )
    return {"session_id": session.id, "driver": driver}

@router.post("/create", 
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Session created successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Create a new browser session",
    description="Creates a new parallel browser session using Browserbase"
)
async def create_session(background_tasks: BackgroundTasks):
    try:
        session_data = create_browser_session()
        session_id = session_data["session_id"]
        active_sessions[session_id] = session_data["driver"]
        
        return JSONResponse(
            content={"session_id": session_id, "status": "created"},
            status_code=201
        )
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@router.post("/{session_id}/navigate",
    response_model=NavigationResponse,
    responses={
        200: {"description": "Navigation successful"},
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Navigation failed"}
    },
    summary="Navigate to URL in session",
    description="Navigate to a specified URL in an existing browser session and analyze the page content"
)
async def navigate(
    navigation: NavigationRequest,
    session_id: str = Path(..., description="ID of the browser session")
):
    if session_id not in active_sessions:
        return JSONResponse(
            content={"error": "Session not found"},
            status_code=404
        )
    
    try:
        driver = active_sessions[session_id]
        driver.get(navigation.url)
        html_content = driver.page_source
        analysis = analyze_page_with_claude(html_content)
        
        return {
            "url": driver.current_url,
            "title": driver.title,
            "analysis": analysis
        }
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@router.delete("/{session_id}",
    responses={
        200: {"description": "Session closed successfully"},
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Failed to close session"}
    },
    summary="Close a browser session",
    description="Closes and cleans up a specific browser session"
)
async def close_session(
    session_id: str = Path(..., description="ID of the browser session to close")
):
    if session_id not in active_sessions:
        return JSONResponse(
            content={"error": "Session not found"},
            status_code=404
        )
    
    try:
        driver = active_sessions[session_id]
        driver.quit()
        del active_sessions[session_id]
        return {"status": "closed"}
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@router.delete("/{session_id}/kill",
    responses={
        200: {"description": "Browser killed successfully"},
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Failed to kill browser"}
    },
    summary="Kill browser process",
    description="Forcefully terminates the browser process without cleanup"
)
async def kill_browser(
    session_id: str = Path(..., description="ID of the browser session to kill")
):
    if session_id not in active_sessions:
        return JSONResponse(
            content={"error": "Session not found"},
            status_code=404
        )
    
    try:
        driver = active_sessions[session_id]
        # Force kill the browser process
        driver.service.process.kill()
        del active_sessions[session_id]
        return {"status": "killed"}
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

def cleanup_sessions():
    """
    Clean up all active sessions
    """
    for session_id, driver in active_sessions.items():
        try:
            driver.quit()
        except:
            pass
    active_sessions.clear()
