from contextlib import asynccontextmanager

from agents.agents import ExecutorAgent, PlannerAgent
from app.core.config import Settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Add any async resources here (database, cache, etc.)
    print("Starting up...")
    yield
    # Shutdown: Clean up any resources
    print("Shutting down...")

app = FastAPI(
    title="AI Agent Backend",
    description="API for AI Agents with Browser Automation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "healthy", "version": "1.0.0"}

# Define the request model
class ExecuteRequest(BaseModel):
    url: str
    intent: str
    context: str

# Initialize agents
planner_agent = PlannerAgent()
executor_agent = ExecutorAgent()

@app.post("/execute")
async def execute(request: ExecuteRequest):
    try:
        # Create a plan using the planner agent
        plan = await planner_agent.create_plan(
            url=request.url,
            intent=request.intent,
            context=request.context
        )
        
        # Execute the plan using the executor agent
        result = await executor_agent.execute_plan(plan)
        
        return {
            "status": "success",
            "data": {
                "plan": plan.dict(),
                "execution_results": result
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }