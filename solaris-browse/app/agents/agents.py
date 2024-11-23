# app/services/agents.py
from anthropic import Anthropic
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
import json
import asyncio
import re

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

def extract_json_from_response(response_text: str) -> dict:
    """Extract JSON object from Claude's response text"""
    # First try to parse the entire response as JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # If that fails, try to find JSON-like content
    try:
        # Find content between curly braces, handling nested structures
        stack = []
        start = -1
        potential_jsons = []
        
        for i, char in enumerate(response_text):
            if char == '{':
                if not stack:
                    start = i
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                    if not stack and start != -1:
                        potential_jsons.append(response_text[start:i+1])
                        start = -1
        
        # Try each potential JSON string
        for json_str in potential_jsons:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
                
        raise ValueError("No valid JSON found in response")
    except Exception as e:
        raise ValueError(f"Error extracting JSON: {str(e)}")

class PlannerAgent:
    def __init__(self, anthropic_api_key: str):
        self.client = Anthropic(api_key=anthropic_api_key)
        
    def _format_state_for_prompt(self, state: BrowserState) -> str:
        """Format browser state into a clear string for the prompt"""
        # Truncate visible text content to avoid format string issues
        visible_text = state.visible_text_content[:500] if state.visible_text_content else ""
        
        return f"""Current Page State:
URL: {state.current_url}
Title: {state.page_title}
Available Interactive Elements:
{json.dumps(state.interactive_elements, indent=2)}
Available Form Fields:
{json.dumps(state.form_fields, indent=2)}
Visible Text Content:
{visible_text}"""

    def get_next_action(self, state: BrowserState, intent: str, history: List[BrowserAction] = None) -> BrowserAction:
        """Generate the next single action based on current state and intent"""
        history_str = ""
        if history:
            history_str = "Previous actions taken:\n" + "\n".join(
                f"- {action.action_type} on {action.selector}" for action in history
            )

        prompt = f"""You are a web automation expert. Given the current state of a webpage and a user's intent, 
determine the SINGLE NEXT action to take. You must respond with ONLY a JSON object and no other text.

Available action types:
- click: Click on an element
- type: Input text into a field
- select: Choose an option from a dropdown
- wait: Wait for an element to appear
- scroll: Scroll to an element

IMPORTANT: When generating selectors, prefer simple, reliable selectors:
1. First try ID: '#elementId'
2. Then try data attributes: '[data-testid="example"]'
3. Then try class: '.className'
4. For links/buttons with text, use: 'a[href*="text"]' or 'button[type="submit"]'
5. Only use complex selectors as a last resort

{self._format_state_for_prompt(state)}

{history_str}

User's Intent: {intent}

Respond with ONLY a JSON object containing these fields:
{{
    "action_type": "The type of action to take",
    "selector": "The specific CSS selector",
    "value": "Any value to input (for type actions)",
    "description": "A clear description of what this action does"
}}

DO NOT include any other text, explanation, or markdown formatting."""

        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract and parse JSON from response
            action_dict = extract_json_from_response(response.content[0].text)
            return BrowserAction(**action_dict)
        except Exception as e:
            print(f"Error in get_next_action: {str(e)}")
            print(f"Raw response: {response.content[0].text if 'response' in locals() else 'No response'}")
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
            
            print(f"\nTrying to find element with selector: {action.selector}")
            
            # First wait for the element to be present
            if not await browser_driver.wait_for_element(action.selector, timeout=10):  # Reduced timeout to 10 seconds
                print(f"Element not found after waiting: {action.selector}")
                
                # Try alternative selectors
                alt_selectors = self._generate_alternative_selectors(action.selector)
                print(f"Trying alternative selectors: {alt_selectors}")
                
                for alt_selector in alt_selectors:
                    print(f"Trying alternative selector: {alt_selector}")
                    if await browser_driver.wait_for_element(alt_selector, timeout=5):
                        print(f"Found element with alternative selector: {alt_selector}")
                        action.selector = alt_selector
                        break
                else:
                    print("No alternative selectors worked")
                    return False
            
            # Execute the action
            print(f"Executing {action.action_type} on {action.selector}")
            success = await func(browser_driver, action)
            
            if success:
                print(f"Action executed successfully")
                # Validate the action
                success = await self._validate_action(browser_driver, action)
                if success:
                    print("Action validated successfully")
                else:
                    print("Action validation failed")
            else:
                print(f"Action execution failed")
            
            return success
        except Exception as e:
            print(f"Error executing action: {str(e)}")
            return False

    def _generate_alternative_selectors(self, original_selector: str) -> List[str]:
        """Generate alternative selectors based on the original selector"""
        alternatives = []
        
        # If original uses :contains
        if ":contains(" in original_selector:
            text = re.search(r":contains\('(.+?)'\)", original_selector).group(1)
            # Try partial link text
            alternatives.extend([
                f"a[href*='{text.lower()}']",  # href contains text
                f"a[href*='{text.upper()}']",  # href contains uppercase text
                f"//a[contains(text(), '{text}')]",  # XPath with text contains
                f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"  # Case-insensitive XPath
            ])
        
        return alternatives

    async def _validate_action(self, browser_driver, action: BrowserAction) -> bool:
        """Validate that an action was successful"""
        prompt = f"""Given this browser action:
{json.dumps(action.dict(), indent=2)}

Generate a SINGLE validation check to verify the action succeeded.
The validation must use proper CSS selectors.
Respond ONLY with a JSON object containing:
{{
    "validation_type": "visibility | value | state_change",
    "selector": "The specific CSS selector",
    "expected_value": "The expected value or state (if applicable)"
}}

DO NOT include any other text or explanation."""

        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=500,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            validation = extract_json_from_response(response.content[0].text)
            print(f"Validation check: {validation}")
            
            # Perform the validation check
            if validation["validation_type"] == "visibility":
                result = await browser_driver.is_element_visible(validation["selector"])
                print(f"Visibility check result: {result}")
                return result
            elif validation["validation_type"] == "value":
                actual_value = await browser_driver.get_element_value(validation["selector"])
                print(f"Value check - Expected: {validation['expected_value']}, Actual: {actual_value}")
                return actual_value == validation["expected_value"]
            elif validation["validation_type"] == "state_change":
                # Wait a moment for state to change
                await asyncio.sleep(1)
                result = await browser_driver.is_element_visible(validation["selector"])
                print(f"State change check result: {result}")
                return result
            
            return False
        except Exception as e:
            print(f"Validation error: {str(e)}")
            print(f"Raw response: {response.content[0].text if 'response' in locals() else 'No response'}")
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
        try:
            # Get basic page info
            current_url = browser_driver.current_url()
            page_title = browser_driver.get_title()
            page_content = browser_driver.get_page_source()
            
            print(f"\nCurrent URL: {current_url}")
            print(f"Page Title: {page_title}")
            
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
            
            print("\nInteractive Elements found:")
            for elem in interactive_elements:
                print(f"- {elem['tag']}: {elem['text']} (selector: {elem['selector']})")
            
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
        except Exception as e:
            print(f"Error getting browser state: {str(e)}")
            raise
    
    def _generate_selector(self, elem) -> str:
        """Generate a reliable CSS selector for an element"""
        if elem.get('id'):
            return f"#{elem.get('id')}"
        elif elem.get('name'):
            return f"[name='{elem.get('name')}']"
        elif elem.get('class'):
            return f".{' .'.join(elem.get('class'))}"
        else:
            # Create a selector based on tag and href for links
            if elem.name == 'a' and elem.get('href'):
                return f"a[href*='{elem.get('href')}']"
            # Create a selector based on tag and type for inputs
            elif elem.name == 'input' and elem.get('type'):
                return f"input[type='{elem.get('type')}']"
            # Create a selector based on tag and text content
            text = elem.get_text(strip=True)
            if text:
                return f"{elem.name}[text*='{text}']"
            return elem.name
    
    async def execute_intent(self, browser_driver, intent: str, max_steps: int = 10) -> bool:
        """Execute user intent through planning and execution loop"""
        steps_taken = 0
        self.action_history = []
        
        while steps_taken < max_steps:
            print(f"\nStep {steps_taken + 1}")
            try:
                # Get current state
                current_state = await self.get_browser_state(browser_driver)
                
                # Get next action
                next_action = self.planner.get_next_action(
                    current_state, 
                    intent,
                    self.action_history
                )
                print(f"Next Action: {next_action}")
                
                # Execute action
                success = await self.executor.execute_action(next_action, browser_driver)
                
                if success:
                    print(f"Action successful: {next_action}")
                    self.action_history.append(next_action)
                    steps_taken += 1
                    
                    # Check if intent is satisfied
                    if await self._check_intent_satisfied(browser_driver, intent, current_state):
                        return True
                else:
                    print(f"Failed to execute action: {next_action}")
                    return False
            except Exception as e:
                print(f"Error in execute_intent: {str(e)}")
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

Respond with ONLY 'true' if the intent is satisfied, or 'false' if more actions are needed.
DO NOT include any other text or explanation."""

        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=100,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text.strip().lower() == 'true'
        except Exception as e:
            print(f"Error checking intent satisfaction: {str(e)}")
            return False
