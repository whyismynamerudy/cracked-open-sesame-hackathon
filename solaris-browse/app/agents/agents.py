# app/services/agents.py
from anthropic import Anthropic
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
import json
import asyncio

class BrowserAction(BaseModel):
    """Represents a single browser action to be executed"""
    action_type: str = Field(..., description="Type of action: click, type, select, scroll, wait")
    selector: str = Field(..., description="CSS selector or XPath for the element")
    value: Optional[str] = Field(None, description="Value to input if action requires it")
    description: str = Field(..., description="Human readable description of what this action does")

class BrowserState(BaseModel):
    """Represents the current state of the browser"""
    current_url: str
    page_title: str
    page_text: str
    interactive_elements: List[Dict[str, str]]  # List of clickable/interactive elements
    visible_text_content: str
    form_fields: List[Dict[str, str]]  # List of input fields and their types

class PlannerAgent:
    def __init__(self, anthropic_api_key: str):
        self.client = Anthropic(api_key=anthropic_api_key)
        
    def _format_state_for_prompt(self, state: BrowserState) -> str:
        """Format browser state into a clear string for the prompt"""
        return f"""Current Page State:
- URL: {state.current_url}
- Title: {state.page_title}
- Available Interactive Elements:
{json.dumps(state.interactive_elements, indent=2)}
- Available Form Fields:
{json.dumps(state.form_fields, indent=2)}
- Visible Text Content:
{state.visible_text_content[:500]}  # First 500 chars for context
"""

    def get_next_action(self, state: BrowserState, intent: str, history: List[BrowserAction] = None) -> BrowserAction:
        """Generate the next single action based on current state and intent"""
        history_str = ""
        if history:
            history_str = "Previous actions taken:\n" + "\n".join(
                f"- {action.action_type} on {action.selector}" for action in history
            )

        prompt = f"""You are a web automation expert. Given the current state of a webpage and a user's intent, 
determine the SINGLE NEXT action to take. Generate specific, executable browser actions.

Available action types:
- click: Click on an element
- type: Input text into a field
- select: Choose an option from a dropdown
- wait: Wait for an element to appear
- scroll: Scroll to an element

IMPORTANT: When generating selectors, you MUST use proper CSS selectors. For example:
- To select by ID: '#elementId'
- To select by class: '.className'
- To select by attribute: '[data-testid="example"]'
- To select by text content: 'a:contains("Link Text")'
- To select nested elements: '.parent .child'
DO NOT use text-based selectors like 'a[text="example"]'.

{self._format_state_for_prompt(state)}

{history_str}

User's Intent: {intent}

Generate a single next action in JSON format with these fields:
- action_type: The type of action to take
- selector: The specific CSS selector (following the rules above)
- value: Any value to input (for type actions)
- description: A clear description of what this action does

Think through this step-by-step:
1. What is the immediate next action needed to progress toward the intent?
2. What is the most reliable way to identify the target element using CSS selectors?
3. What should happen after this action succeeds?

Respond ONLY with the JSON object for the next action."""

        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            action_dict = json.loads(response.content[0].text)
            return BrowserAction(**action_dict)
        except Exception as e:
            print(f"Error parsing Claude's response: {e}")
            print(f"Raw response: {response.content[0].text}")
            raise

class ExecutorAgent:
    def __init__(self, anthropic_api_key: str):
        self.client = Anthropic(api_key=anthropic_api_key)
        
        # Available browser interaction functions
        self.browser_functions = {
            "click": self._click_element,
            "type": self._type_text,
            "select": self._select_option,
            "wait": self._wait_for_element,
            "scroll": self._scroll_to_element
        }
    
    async def execute_action(self, action: BrowserAction, browser_driver) -> bool:
        """Execute a browser action and return success status"""
        try:
            func = self.browser_functions.get(action.action_type)
            if not func:
                raise ValueError(f"Unknown action type: {action.action_type}")
            
            # First wait for the element to be present
            if not await browser_driver.wait_for_element(action.selector):
                print(f"Element not found: {action.selector}")
                return False
            
            # Execute the action
            success = await func(browser_driver, action)
            
            # Validate the action
            if success:
                success = await self._validate_action(browser_driver, action)
            
            return success
        except Exception as e:
            print(f"Error executing action: {str(e)}")
            return False

    async def _validate_action(self, browser_driver, action: BrowserAction) -> bool:
        """Validate that an action was successful"""
        prompt = f"""Given this browser action:
{json.dumps(action.dict(), indent=2)}

Generate a SINGLE validation check to verify the action succeeded.
The validation must use proper CSS selectors.
Respond only with a JSON object containing:
- validation_type: "visibility" | "value" | "state_change"
- selector: The CSS selector to check
- expected_value: The expected value or state (if applicable)"""

        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=500,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        try:
            validation = json.loads(response.content[0].text)
            
            # Perform the validation check
            if validation["validation_type"] == "visibility":
                return await browser_driver.is_element_visible(validation["selector"])
            elif validation["validation_type"] == "value":
                actual_value = await browser_driver.get_element_value(validation["selector"])
                return actual_value == validation["expected_value"]
            elif validation["validation_type"] == "state_change":
                # Wait a moment for state to change
                await asyncio.sleep(1)
                return await browser_driver.is_element_visible(validation["selector"])
            
            return False
        except Exception as e:
            print(f"Validation error: {str(e)}")
            return False

    # Browser interaction functions
    async def _click_element(self, browser_driver, action: BrowserAction) -> bool:
        return await browser_driver.click_element(action.selector)
        
    async def _type_text(self, browser_driver, action: BrowserAction) -> bool:
        return await browser_driver.input_text(action.selector, action.value)
        
    async def _select_option(self, browser_driver, action: BrowserAction) -> bool:
        return await browser_driver.select_option(action.selector, action.value)
        
    async def _wait_for_element(self, browser_driver, action: BrowserAction) -> bool:
        return await browser_driver.wait_for_element(action.selector)
        
    async def _scroll_to_element(self, browser_driver, action: BrowserAction) -> bool:
        return await browser_driver.scroll_to_element(action.selector)

class AutomationOrchestrator:
    def __init__(self, anthropic_api_key: str):
        self.planner = PlannerAgent(anthropic_api_key)
        self.executor = ExecutorAgent(anthropic_api_key)
        self.action_history: List[BrowserAction] = []
        
    async def get_browser_state(self, browser_driver) -> BrowserState:
        """Capture current browser state"""
        # Get basic page info
        current_url = browser_driver.current_url()
        page_title = browser_driver.get_title()
        page_content = browser_driver.get_page_source()
        
        # Parse page content
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # Get interactive elements
        interactive_elements = []
        for elem in soup.find_all(['a', 'button', 'input[type="submit"]']):
            interactive_elements.append({
                "tag": elem.name,
                "id": elem.get('id', ''),
                "text": elem.get_text(strip=True),
                "selector": self._generate_selector(elem)
            })
        
        # Get form fields
        form_fields = []
        for elem in soup.find_all(['input', 'textarea', 'select']):
            form_fields.append({
                "type": elem.get('type', 'text'),
                "id": elem.get('id', ''),
                "name": elem.get('name', ''),
                "placeholder": elem.get('placeholder', ''),
                "selector": self._generate_selector(elem)
            })
        
        # Get visible text
        visible_text = " ".join(elem.get_text(strip=True) 
                              for elem in soup.find_all(text=True) 
                              if elem.parent.name not in ['style', 'script'])
        
        return BrowserState(
            current_url=current_url,
            page_title=page_title,
            page_text=page_content,
            interactive_elements=interactive_elements,
            visible_text_content=visible_text,
            form_fields=form_fields
        )
    
    def _generate_selector(self, elem) -> str:
        """Generate a reliable CSS selector for an element"""
        if elem.get('id'):
            return f"#{elem.get('id')}"
        elif elem.get('name'):
            return f"[name='{elem.get('name')}']"
        elif elem.get('class'):
            return f".{' .'.join(elem.get('class'))}"
        else:
            # Create a selector based on tag and text content
            text = elem.get_text(strip=True)
            if text:
                return f"{elem.name}:contains('{text}')"
            return elem.name
    
    async def execute_intent(self, browser_driver, intent: str, max_steps: int = 10) -> bool:
        """Execute user intent through planning and execution loop"""
        steps_taken = 0
        self.action_history = []
        
        while steps_taken < max_steps:
            # Get current state
            current_state = await self.get_browser_state(browser_driver)
            
            # Get next action
            try:
                next_action = self.planner.get_next_action(
                    current_state, 
                    intent,
                    self.action_history
                )
            except Exception as e:
                print(f"Planning error: {str(e)}")
                return False
            
            # Execute action
            success = await self.executor.execute_action(next_action, browser_driver)
            
            if success:
                self.action_history.append(next_action)
                steps_taken += 1
                
                # Check if intent is satisfied
                if await self._check_intent_satisfied(browser_driver, intent, current_state):
                    return True
            else:
                print(f"Failed to execute action: {next_action}")
                return False
                
        return False
    
    async def _check_intent_satisfied(self, browser_driver, intent: str, state: BrowserState) -> bool:
        """Check if the user's intent has been satisfied"""
        prompt = f"""Given the user's intent and current page state, determine if the intent has been satisfied.

Intent: {intent}

Current State:
{self._format_state_for_prompt(state)}

Previous Actions:
{json.dumps([action.dict() for action in self.action_history], indent=2)}

Respond with ONLY 'true' if the intent is satisfied, or 'false' if more actions are needed."""

        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=100,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text.strip().lower() == 'true'
