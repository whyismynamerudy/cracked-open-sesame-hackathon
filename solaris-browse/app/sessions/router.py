import os
from contextlib import contextmanager
from typing import Dict, List

import requests
from anthropic import Anthropic
from app.agents.agents import AutomationOrchestrator
from browserbase import Browserbase
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Path, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
orchestrator = AutomationOrchestrator(CLAUDE_API_KEY)

# Store active sessions in a class to handle reloads better
class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, webdriver.Remote] = {}
    
    def add_session(self, session_id: str, driver: webdriver.Remote):
        self._sessions[session_id] = driver
    
    def get_session(self, session_id: str) -> webdriver.Remote:
        return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def get_all_sessions(self) -> Dict[str, webdriver.Remote]:
        return self._sessions.copy()
    
    def cleanup(self):
        for session_id, driver in list(self._sessions.items()):
            try:
                driver.quit()
            except:
                pass
            self.remove_session(session_id)

# Create global session manager
session_manager = SessionManager()

def cleanup_sessions():
    """
    Clean up all active sessions
    """
    session_manager.cleanup()

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

class SessionStatus(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the browser session")
    status: str = Field(..., description="Current status of the session")
    url: str = Field(default="unknown", description="Current URL of the session")
    title: str = Field(default="unknown", description="Current page title")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "status": "active",
                "url": "https://example.com",
                "title": "Example Domain"
            }
        }

class SessionListResponse(BaseModel):
    sessions: List[SessionStatus] = Field(..., description="List of sessions and their status")
    count: int = Field(..., description="Total number of sessions")

    class Config:
        json_schema_extra = {
            "example": {
                "sessions": [
                    {
                        "session_id": "sess_abc123",
                        "status": "active",
                        "url": "https://example.com",
                        "title": "Example Domain"
                    }
                ],
                "count": 1
            }
        }

class NavigationRequest(BaseModel):
    url: str = Field(..., description="URL to navigate to", example="https://www.ontario.ca/page/government-ontario")
    intent: str = Field(default="Find info on OSAP", description="User's automation intent")

class NavigationResponse(BaseModel):
    url: str = Field(..., description="Current URL after navigation")
    title: str = Field(..., description="Page title")
    automation_result: bool = Field(..., description="Whether the automation was successful")
    actions_taken: List[Dict] = Field(..., description="List of actions taken during automation")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "title": "Example Domain",
                "analysis": "This appears to be a simple webpage with a heading and brief description..."
            }
        }

class SeleniumBrowserDriver:
    def __init__(self, selenium_driver):
        self.driver = selenium_driver
        self.wait = WebDriverWait(self.driver, 10)
        self.actions = ActionChains(self.driver)
    
    def current_url(self) -> str:
        return self.driver.current_url
    
    def get_title(self) -> str:
        return self.driver.title
    
    def get_page_source(self) -> str:
        return self.driver.page_source

    def _find_element(self, selector: str):
        """Find element using multiple strategies"""
        try:
            # Try CSS selector first
            return self.driver.find_element(By.CSS_SELECTOR, selector)
        except Exception:
            try:
                # Try finding by text content using XPath
                # Use double quotes for XPath string to avoid escaping
                clean_text = selector.replace('"', "'")
                xpath = f'//*[contains(text(), "{clean_text}")]'
                return self.driver.find_element(By.XPATH, xpath)
            except Exception:
                try:
                    # Try partial link text
                    return self.driver.find_element(By.PARTIAL_LINK_TEXT, selector)
                except Exception as e:
                    print(f"Element not found with any strategy: {selector}")
                    raise e
    
    async def click_element(self, selector: str) -> bool:
        try:
            element = self._find_element(selector)
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            # Wait for element to be clickable
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            # Try regular click first
            try:
                element.click()
            except Exception:
                # If regular click fails, try JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e:
            print(f"Click error: {str(e)}")
            return False
    
    async def input_text(self, selector: str, value: str) -> bool:
        try:
            element = self._find_element(selector)
            element.clear()
            element.send_keys(value)
            return True
        except Exception as e:
            print(f"Input error: {str(e)}")
            return False
    
    async def select_option(self, selector: str, value: str) -> bool:
        try:
            element = self._find_element(selector)
            element.click()
            option = self.driver.find_element(By.CSS_SELECTOR, f'{selector} option[value="{value}"]')
            option.click()
            return True
        except Exception as e:
            print(f"Select error: {str(e)}")
            return False
    
    async def wait_for_element(self, selector: str, timeout: int = 60) -> bool:
        try:
            def find_with_multiple_strategies(driver):
                try:
                    return driver.find_element(By.CSS_SELECTOR, selector)
                except Exception:
                    try:
                        clean_text = selector.replace('"', "'")
                        xpath = f'//*[contains(text(), "{clean_text}")]'
                        return driver.find_element(By.XPATH, xpath)
                    except Exception:
                        return driver.find_element(By.PARTIAL_LINK_TEXT, selector)
            
            element = WebDriverWait(self.driver, timeout).until(find_with_multiple_strategies)
            return element is not None
        except Exception as e:
            print(f"Wait error: {str(e)}")
            return False
    
    async def scroll_to_element(self, selector: str) -> bool:
        try:
            element = self._find_element(selector)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            return True
        except Exception as e:
            print(f"Scroll error: {str(e)}")
            return False

    async def is_element_visible(self, selector: str, timeout: int = 10) -> bool:
        try:
            def check_visibility_with_multiple_strategies(driver):
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    return element.is_displayed()
                except Exception:
                    try:
                        clean_text = selector.replace('"', "'")
                        xpath = f'//*[contains(text(), "{clean_text}")]'
                        element = driver.find_element(By.XPATH, xpath)
                        return element.is_displayed()
                    except Exception:
                        element = driver.find_element(By.PARTIAL_LINK_TEXT, selector)
                        return element.is_displayed()
            
            return WebDriverWait(self.driver, timeout).until(check_visibility_with_multiple_strategies)
        except Exception as e:
            print(f"Visibility check error: {str(e)}")
            return False

    async def get_element_value(self, selector: str) -> str:
        try:
            element = self._find_element(selector)
            return element.get_attribute("value") or ""
        except Exception as e:
            print(f"Get value error: {str(e)}")
            return ""

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
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-popup-blocking')
    driver = webdriver.Remote(
        command_executor=connection, options=options  # type: ignore
    )
    debugger_url = session.debugger_full_screen_url
    return {"session_id": session.id, "driver": driver, "debugger_url": debugger_url}

def get_browserbase_sessions() -> List[Dict]:
    """
    Get all sessions from Browserbase API
    """
    url = f"https://api.browserbase.com/v1/projects/{BROWSERBASE_PROJECT_ID}/sessions"
    headers = {"Authorization": f"X-BB-API-Key {BROWSERBASE_API_KEY}"}
    
    try:
        url = "https://www.browserbase.com/v1/sessions"
        headers = {"X-BB-API-Key": BROWSERBASE_API_KEY}
        response = requests.request("GET", url, headers=headers)
        return response.json()
    except Exception:
        return []

def is_session_alive(session_id: str) -> bool:
    """
    Check if a session is still alive according to Browserbase API
    """
    sessions = get_browserbase_sessions()
    return any(s.get("id") == session_id and s.get("status") == "active" for s in sessions)

@router.get("/",
    response_model=SessionListResponse,
    responses={
        200: {"description": "Successfully retrieved alive sessions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="List alive sessions",
    description="Returns a list of all active and responsive browser sessions"
)
async def getSessionList():
    try:
        sessions = get_browserbase_sessions()
        print(sessions)
        session_list = []
        active_sessions = session_manager.get_all_sessions()
        for session in sessions:
            session_id = session.get("id")
            if session_id in active_sessions:
                driver = active_sessions[session_id]
                session_list.append({
                    "session_id": session_id,
                    "status": "active",
                    "url": driver.current_url,
                    "title": driver.title
                })
            else:
                session_list.append({
                    "session_id": session_id,
                    "status": "inactive"
                })
        
        return {
            "sessions": session_list,
            "count": len(session_list)
        }
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

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
        debugger_url = session_data["debugger_url"]
        session_manager.add_session(session_id, session_data["driver"])
        
        return JSONResponse(
            content={"session_id": session_id, "status": "created", "debugger_url": debugger_url},
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
    driver = session_manager.get_session(session_id)
    if not driver:
        return JSONResponse(
            content={"error": "Session not found"},
            status_code=404
        )
    
    try:
        # Wrap Selenium driver in our adapter
        browser_driver = SeleniumBrowserDriver(driver)
        print(browser_driver.current_url())
        # Navigate to URL
        driver.get(navigation.url)
        print(driver.current_url)
        
        # Wait for page load
        print("waiting for page load")
        WebDriverWait(driver, 10).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete'
        )
        print("page loaded")
        
        
        # Execute automation with the orchestrator
        success = await orchestrator.execute_intent(
            browser_driver,
            navigation.intent
        )
        print(success)
        print("automation done")
        
        return {
            "url": browser_driver.current_url(),
            "title": browser_driver.get_title(),
            "automation_result": success,
            "actions_taken": [action.dict() for action in orchestrator.action_history]
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
    driver = session_manager.get_session(session_id)
    if not driver:
        return JSONResponse(
            content={"error": "Session not found"},
            status_code=404
        )
    
    try:
        driver.quit()
        session_manager.remove_session(session_id)
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
    driver = session_manager.get_session(session_id)
    if not driver:
        return JSONResponse(
            content={"error": "Session not found"},
            status_code=404
        )
    
    try:
        # Force kill the browser process
        driver.service.process.kill()
        session_manager.remove_session(session_id)
        return {"status": "killed"}
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
