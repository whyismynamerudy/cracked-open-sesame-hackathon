from typing import Dict, List

from app.core.config import settings
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.callbacks import LangfuseCallbackHandler
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langfuse import Langfuse
from langfuse.openai import OpenAITracingMiddleware
from pydantic import BaseModel

# Initialize Langfuse
langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST  # Optional, defaults to cloud version
)

# Create callback handler for LangChain
langfuse_callback = LangfuseCallbackHandler(
    langfuse_client=langfuse,
    trace_name="ai_agent_execution",
)

class ActionStep(BaseModel):
    action: str
    args: Dict

class Plan(BaseModel):
    steps: List[ActionStep]
    reasoning: str

class PlannerAgent:
    def __init__(self, model_name: str = "gpt-4"):
        # Initialize LLM with Langfuse tracing
        self.llm = ChatOpenAI(
            model_name=model_name, 
            temperature=0,
            callbacks=[langfuse_callback]
        )
        
        # Define the planner prompt
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a planning agent that breaks down user intents into specific actionable steps.
            Given a URL and a user intent, create a detailed plan of browser automation steps.
            Your plan should be specific and actionable, focusing on web interactions."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ])

        # Create the planner agent
        self.agent = create_structured_chat_agent(
            llm=self.llm,
            prompt=self.prompt,
            tools=[],  # Planner doesn't need tools as it just creates plans
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=[],
            verbose=True,
            callbacks=[langfuse_callback],
        )

    async def create_plan(self, url: str, intent: str, context: str) -> Plan:
        # Create a new trace for this planning session
        with langfuse.trace(
            name="create_plan",
            metadata={
                "url": url,
                "intent": intent,
            }
        ) as trace:
            input_text = f"URL: {url}\nIntent: {intent}\nContext: {context}\n\nCreate a detailed plan for achieving this intent."
            
            # Log the input
            trace.log(
                name="plan_input",
                level="INFO",
                metadata={
                    "url": url,
                    "intent": intent,
                    "context": context
                }
            )
            
            result = await self.agent_executor.ainvoke({"input": input_text})
            
            # Log the output plan
            trace.log(
                name="plan_output",
                level="INFO",
                metadata={"raw_result": result}
            )
            
            # Parse the result into a structured plan
            plan = Plan(
                steps=[
                    ActionStep(action=step["action"], args=step["args"])
                    for step in result["steps"]
                ],
                reasoning=result["reasoning"]
            )
            
            return plan

class ExecutorAgent:
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(
            model_name=model_name, 
            temperature=0,
            callbacks=[langfuse_callback]
        )
        
        self.tools = [
            Tool(
                name="navigate",
                func=self._navigate,
                description="Navigate to a specific URL"
            ),
            Tool(
                name="click",
                func=self._click,
                description="Click on an element matching the selector"
            ),
            Tool(
                name="type",
                func=self._type,
                description="Type text into an input field"
            ),
        ]

        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an execution agent that performs web automation tasks.
            You have access to tools for navigating, clicking, and typing.
            Execute each step in the plan precisely and report the results."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ])

        self.agent = create_structured_chat_agent(
            llm=self.llm,
            prompt=self.prompt,
            tools=self.tools,
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            callbacks=[langfuse_callback],
        )

    async def execute_plan(self, plan: Plan) -> Dict:
        with langfuse.trace(
            name="execute_plan",
            metadata={"plan": plan.dict()}
        ) as trace:
            results = []
            for step in plan.steps:
                # Create a span for each step execution
                with trace.span(
                    name=f"execute_step_{step.action}",
                    metadata={"step": step.dict()}
                ) as span:
                    result = await self.agent_executor.ainvoke({
                        "input": f"Execute step: {step.action} with arguments: {step.args}"
                    })
                    results.append(result)
                    span.log(
                        name="step_result",
                        level="INFO",
                        metadata={"result": result}
                    )
            
            return {"status": "success", "results": results}

    # Tool implementation methods
    async def _navigate(self, url: str):
        with langfuse.trace(name="navigate", metadata={"url": url}):
            # Implement navigation logic
            return f"Navigated to {url}"

    async def _click(self, selector: str):
        with langfuse.trace(name="click", metadata={"selector": selector}):
            # Implement click logic
            return f"Clicked element matching {selector}"

    async def _type(self, selector: str, text: str):
        with langfuse.trace(
            name="type",
            metadata={"selector": selector, "text": text}
        ):
            # Implement typing logic
            return f"Typed '{text}' into element matching {selector}"