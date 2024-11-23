from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any

from .agents import PlannerAgent, ExecutorAgent, Plan

router = APIRouter(
    prefix="/agent",
    tags=["agents"],
    responses={500: {"description": "Internal server error"}}
)

class ExecuteRequest(BaseModel):
    url: str = Field(..., description="URL to navigate to")
    intent: str = Field(..., description="User's intent for the automation")
    context: str = Field(..., description="Additional context for the automation")

class ExecuteResponse(BaseModel):
    status: str = Field(..., description="Status of the execution")
    data: Dict[str, Any] = Field(..., description="Execution results including plan and results")

# Initialize agents
planner_agent = PlannerAgent()
executor_agent = ExecutorAgent()

@router.post("/execute",
    response_model=ExecuteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Execution successful"},
        500: {"description": "Execution failed"}
    },
    summary="Execute automated task",
    description="Creates and executes a plan for the given URL and intent using AI agents"
)
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
        return JSONResponse(
            content={"status": "error", "error": str(e)},
            status_code=500
        )
