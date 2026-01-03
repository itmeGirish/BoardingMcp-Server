"""
Interactive Onboarding Workflow

Flow:
1. Frontend sends user_id + business_profile data → Execute create_business_node
2. Frontend receives result → Sends project data → Execute create_project_node  
3. Frontend receives result → Sends embedded_signup data → Execute create_embedding_node
4. Workflow complete
"""


from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, TypedDict, Any, Optional, Literal
from dataclasses import dataclass

from .config import logging
from .state import (
    CreateBusinessProfileState,
    CreateProjectState,
    EmbeddedSignupUrlState,
)


class OnboardingState(TypedDict):
    """Complete onboarding workflow state"""
    # Shared user identifier - passed once at start
    user_id: str
    
    # Current step tracking
    current_step: Literal["business_profile", "project", "embedded_signup", "completed"]
    
    # Input data for each step (populated incrementally from frontend)
    business_profile: Optional[CreateBusinessProfileState]
    project: Optional[CreateProjectState]
    embedded_signup: Optional[EmbeddedSignupUrlState]
    
    # MCP tools reference
    mcp_tools: Dict[str, Any]
    
    # Results from each step
    business_profile_result: Optional[Dict[str, Any]]
    project_result: Optional[Dict[str, Any]]
    embedded_signup_result: Optional[Dict[str, Any]]
    
    # Error tracking
    error: Optional[str]


@dataclass
class OnboardingFlow:
    """
    Interactive onboarding workflow using LangGraph.
    
    Each node executes and then waits for frontend to provide next step's data.
    Uses LangGraph's interrupt/resume pattern for human-in-the-loop flow.
    """
    
    mcp_tools: Dict[str, Any]

    async def create_business_node(self, state: OnboardingState) -> Dict[str, Any]:
        """
        Step 1: Business profile creation.
        
        Expects: user_id + business_profile data from frontend
        Returns: business_profile_result, advances to 'project' step
        """
        business_creation_tool = state["mcp_tools"].get("create_business_profile")
        
        if not business_creation_tool:
            return {"error": "create_business_profile tool not found"}
        
        if not state.get("business_profile"):
            return {"error": "business_profile data not provided"}
        
        try:
            # Inject user_id into business profile data
            profile_data = {
                **state["business_profile"],
                "user_id": state["user_id"],
            }
            
            result = await business_creation_tool.ainvoke(profile_data)
            logging.info("Business profile created successfully for user: %s", state["user_id"])
            
            return {
                "business_profile_result": result,
                "current_step": "project",  # Advance to next step
                "error": None,
            }
        except Exception as e:
            error_msg = f"Business creation failed: {e}"
            logging.error(error_msg)
            return {"error": error_msg}

    async def create_project_node(self, state: OnboardingState) -> Dict[str, Any]:
        """
        Step 2: Project creation.
        
        Expects: project data from frontend (after business_profile completed)
        Returns: project_result, advances to 'embedded_signup' step
        """
        if state.get("error"):
            return {}
        
        create_project_tool = state["mcp_tools"].get("create_project")
        
        if not create_project_tool:
            return {"error": "create_project tool not found"}
        
        if not state.get("project"):
            return {"error": "project data not provided"}
        
        try:
            # Inject user_id into project data
            project_data = {
                **state["project"],
                "user_id": state["user_id"],
            }
            
            result = await create_project_tool.ainvoke(project_data)
            logging.info("Project created successfully: %s for user: %s", 
                        project_data.get("name"), state["user_id"])
            
            return {
                "project_result": result,
                "current_step": "embedded_signup",  # Advance to next step
                "error": None,
            }
        except Exception as e:
            error_msg = f"Project creation failed: {e}"
            logging.error(error_msg)
            return {"error": error_msg}

    async def create_embedding_node(self, state: OnboardingState) -> Dict[str, Any]:
        """
        Step 3: Embedded signup URL creation.
        
        Expects: embedded_signup data from frontend (after project completed)
        Returns: embedded_signup_result, marks workflow as 'completed'
        """
        if state.get("error"):
            return {}
        
        create_embedding_tool = state["mcp_tools"].get("generate_embedded_signup_url")
        
        if not create_embedding_tool:
            return {"error": "generate_embedded_signup_url tool not found"}
        
        if not state.get("embedded_signup"):
            return {"error": "embedded_signup data not provided"}
        
        try:
            embedding_data = state["embedded_signup"]
            
            result = await create_embedding_tool.ainvoke(embedding_data)
            logging.info("Embedded signup URL created successfully for: %s", 
                        embedding_data.get("business_name"))
            
            return {
                "embedded_signup_result": result,
                "current_step": "completed",  # Workflow finished
                "error": None,
            }
        except Exception as e:
            error_msg = f"Embedded URL creation failed: {e}"
            logging.error(error_msg)
            return {"error": error_msg}

    def should_continue(self, state: OnboardingState) -> str:
        """Route based on error state."""
        if state.get("error"):
            return "handle_error"
        return "continue"

    async def handle_error_node(self, state: OnboardingState) -> Dict[str, Any]:
        """Error handling node."""
        error = state.get("error", "Unknown error occurred")
        logging.error("Workflow error: %s", error)
        return {"error": error}

    def build_workflow(self) -> StateGraph:
        """Build the interactive workflow graph."""
        builder = StateGraph(OnboardingState)
        
        # Add nodes
        builder.add_node("create_business_node", self.create_business_node)
        builder.add_node("create_project_node", self.create_project_node)
        builder.add_node("create_embedding_node", self.create_embedding_node)
        builder.add_node("handle_error", self.handle_error_node)

        # Linear flow with error handling
        builder.add_edge(START, "create_business_node")
        
        builder.add_conditional_edges(
            "create_business_node",
            self.should_continue,
            {"continue": "create_project_node", "handle_error": "handle_error"}
        )
        
        builder.add_conditional_edges(
            "create_project_node",
            self.should_continue,
            {"continue": "create_embedding_node", "handle_error": "handle_error"}
        )
        
        builder.add_edge("create_embedding_node", END)
        builder.add_edge("handle_error", END)
        
        # Add checkpointer for state persistence between steps
        memory = MemorySaver()
        return builder.compile(checkpointer=memory)


class OnboardingSession:
    """
    Manages an interactive onboarding session.
    
    Usage:
        session = OnboardingSession(mcp_tools, user_id)
        
        # Step 1: Business profile
        result1 = await session.start(business_profile_data)
        
        # Step 2: Project (frontend collects data, then calls)
        result2 = await session.submit_project(project_data)
        
        # Step 3: Embedded signup (frontend collects data, then calls)
        result3 = await session.submit_embedded_signup(embedded_signup_data)
    """
    
    def __init__(self, mcp_tools: Dict[str, Any], user_id: str):
        self.mcp_tools = mcp_tools
        self.user_id = user_id
        self.flow = OnboardingFlow(mcp_tools=mcp_tools)
        self.workflow = self.flow.build_workflow()
        self.thread_id = f"onboarding_{user_id}"
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self._state: Optional[OnboardingState] = None
    
    async def start(self, business_profile: CreateBusinessProfileState) -> Dict[str, Any]:
        """
        Start onboarding with user_id and business profile data.
        
        Returns result of business profile creation.
        Frontend should then collect project data for next step.
        """
        initial_state: OnboardingState = {
            "user_id": self.user_id,
            "current_step": "business_profile",
            "business_profile": business_profile,
            "project": None,
            "embedded_signup": None,
            "mcp_tools": self.mcp_tools,
            "business_profile_result": None,
            "project_result": None,
            "embedded_signup_result": None,
            "error": None,
        }
        
        # Run only the first node
        result = await self.workflow.ainvoke(
            initial_state,
            self.config,
        )
        self._state = result
        
        return {
            "success": result.get("error") is None,
            "current_step": result.get("current_step"),
            "business_profile_result": result.get("business_profile_result"),
            "error": result.get("error"),
            "next_step": "project" if not result.get("error") else None,
        }
    
    async def submit_project(self, project: CreateProjectState) -> Dict[str, Any]:
        """
        Submit project data (Step 2).
        
        Called by frontend after collecting project details.
        Returns result of project creation.
        """
        if not self._state:
            return {"error": "Session not started. Call start() first."}
        
        if self._state.get("current_step") != "project":
            return {"error": f"Invalid step. Current step is: {self._state.get('current_step')}"}
        
        # Update state with project data
        self._state["project"] = project
        
        # Resume workflow
        result = await self.workflow.ainvoke(
            self._state,
            self.config,
        )
        self._state = result
        
        return {
            "success": result.get("error") is None,
            "current_step": result.get("current_step"),
            "project_result": result.get("project_result"),
            "error": result.get("error"),
            "next_step": "embedded_signup" if not result.get("error") else None,
        }
    
    async def submit_embedded_signup(self, embedded_signup: EmbeddedSignupUrlState) -> Dict[str, Any]:
        """
        Submit embedded signup data (Step 3 - Final).
        
        Called by frontend after collecting embedded signup details.
        Returns final result with embedded signup URL.
        """
        if not self._state:
            return {"error": "Session not started. Call start() first."}
        
        if self._state.get("current_step") != "embedded_signup":
            return {"error": f"Invalid step. Current step is: {self._state.get('current_step')}"}
        
        # Update state with embedded signup data
        self._state["embedded_signup"] = embedded_signup
        
        # Resume workflow
        result = await self.workflow.ainvoke(
            self._state,
            self.config,
        )
        self._state = result
        
        return {
            "success": result.get("error") is None,
            "current_step": result.get("current_step"),
            "embedded_signup_result": result.get("embedded_signup_result"),
            "error": result.get("error"),
            "completed": result.get("current_step") == "completed",
        }
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current session state for frontend."""
        if not self._state:
            return {"current_step": None, "started": False}
        
        return {
            "current_step": self._state.get("current_step"),
            "user_id": self._state.get("user_id"),
            "business_profile_result": self._state.get("business_profile_result"),
            "project_result": self._state.get("project_result"),
            "embedded_signup_result": self._state.get("embedded_signup_result"),
            "error": self._state.get("error"),
        }


