from typing import Dict

from selenium import webdriver
from selenium.webdriver.remote.remote_connection import RemoteConnection
from browserbase import Browserbase
from dotenv import load_dotenv
import os
from anthropic import Anthropic

load_dotenv()

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

bb = Browserbase(api_key=BROWSERBASE_API_KEY)
anthropic = Anthropic(api_key=CLAUDE_API_KEY)


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

        # Update headers to include the Browserbase required information
        headers["x-bb-api-key"] = BROWSERBASE_API_KEY
        headers["session-id"] = self.session_id

        return headers  # type: ignore


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


def run() -> None:
    # Use the custom class to create and connect to a new browser session
    session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
    connection = BrowserbaseConnection(session.id, session.selenium_remote_url)
    driver = webdriver.Remote(
        command_executor=connection, options=webdriver.ChromeOptions()  # type: ignore
    )

    # Print a bit of info about the browser we've connected to
    print(
        "Connected to Browserbase",
        f"{driver.name} version {driver.caps['browserVersion']}",  # type: ignore
    )

    try:
        # Perform our browser commands
        driver.get("https://www.sfmoma.org")
        print(f"At URL: {driver.current_url} | Title: {driver.title}")
        
        # Get the page HTML
        html_content = driver.page_source
        
        # Analyze the page with Claude
        analysis = analyze_page_with_claude(html_content)
        print("\nClaude's Analysis:")
        print(analysis)

    finally:
        # Make sure to quit the driver so your session is ended!
        driver.quit()


if __name__ == "__main__":
    run()
