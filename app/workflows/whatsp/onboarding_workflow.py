"""
Interactive Onboarding Workflow
Flow:
1. Frontend sends user_id + business_profile data → Execute create_business_node
2. Frontend receives result → Sends project data → Execute create_project_node  
3. Frontend receives result → Sends embedded_signup data → Execute create_embedding_node
4. Workflow complete
"""
from xmlrpc import client
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, TypedDict, Any, Optional, Literal
from dataclasses import dataclass
import json
from app.workflows.whatsp.test_workflow import build_workflow
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from app import logger
from .state import (
    CreateBusinessProfileState,
    CreateProjectState,
    EmbeddedSignupUrlState,
)


class OnboardingState(TypedDict):
    """Complete onboarding workflow state"""
    user_id: str
    current_step: Literal["business_profile", "project", "embedded_signup", "completed"]
    business_profile: Optional[CreateBusinessProfileState]
    project: Optional[CreateProjectState]
    embedded_signup: Optional[EmbeddedSignupUrlState]
    
    
    # Results from each step
    business_profile_result: Optional[Dict[str, Any]]
    project_result: Optional[Dict[str, Any]]
    embedded_signup_result: Optional[Dict[str, Any]]
    
    # Error tracking
    error: Optional[str]


# Global variable to hold MCP tools during workflow execution
# This avoids storing non-serializable tools in state
_current_mcp_tools: Dict[str, Any] = {}


@dataclass
class OnboardingFlow:
    """
    Interactive onboarding workflow using LangGraph.
    
    Each node executes and then waits for frontend to provide next step's data.
    Uses LangGraph's interrupt/resume pattern for human-in-the-loop flow.
    """
    global _current_mcp_tools


    async def show_the_business_node(self, CreateBusinessProfileState) -> CreateBusinessProfileState:
        """Debug node to show current business profile data."""
        return {"business_profile":CreateBusinessProfileState}
 

    async def create_business_node(self, state: OnboardingState) -> Dict[str, Any]:
        """
        Step 1: Business profile creation.
        
        Expects: user_id + business_profile data from frontend
        Returns: business_profile_result, advances to 'project' step
        """
        client = MultiServerMCPClient({
            "FormsMCP": {
                "url": "http://127.0.0.1:8000/mcp",
                "transport": "streamable-http"
            }
        })

        async with client.session("FormsMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}

            business_creation_tool = mcp_tools["create_business_profile"]

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
            if hasattr(result, 'content'):
                result_data = result.content
            else:
                result_data = result 

            if isinstance(result_data, list) and len(result_data) > 0:
                first_item = result_data[0]
                if isinstance(first_item, dict) and first_item.get('type') == 'text':
                    text_content = first_item['text']
                    try:
                        result_data = json.loads(text_content)
                    except:
                        result_data = {"status": "success", "message": text_content}

                return result_data   
            logger.info("Business profile created successfully for user: %s", state["user_id"])

            state["business_profile_result"]=result
            state["current_step"]="business_profile"
            state["error"]=None
            return state
        
        except Exception as e:
            error_msg = f"Business creation failed: {e}"
            logger.error(error_msg)
            state["error"]=error_msg
            return state


    async def show_project_node(self, CreateProjectState) -> CreateProjectState:
        """inpute node of the project data."""

        return {"business_profile":CreateProjectState}
        
    

    async def create_project_node(self, state: OnboardingState) -> Dict[str, Any]:
        """
        Step 2: Project creation.
        
        Expects: project data from frontend (after business_profile completed)
        Returns: project_result, advances to 'embedded_signup' step
        """
        if state.get("error"):
            return f"Sorry, an error occurred couldn't proceed: {state['error']}"
        
        client = MultiServerMCPClient({
            "FormsMCP": {
                "url": "http://127.0.0.1:8000/mcp",
                "transport": "streamable-http"
            }
        })

        async with client.session("FormsMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
        
        create_project_tool = _current_mcp_tools["create_project"]
        
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
            if hasattr(result, 'content'):
                result_data = result.content
            else:
                result_data = result

  
            if isinstance(result_data, str):
                try:
                    result_data = json.loads(result_data)
                except:
                    result_data = {"status": "success", "message": result_data}


            if isinstance(result_data, list):
                if len(result_data) > 0:
                    first_item = result_data[0]
                    
                    if isinstance(first_item, dict):
                        if first_item.get('type') == 'text' and 'text' in first_item:
                            text_content = first_item['text']
                            try:
                                result_data = json.loads(text_content)
                            except:
                                result_data = {"status": "success", "message": text_content}
                        else:
                            result_data = first_item
                    elif hasattr(first_item, 'text'):
                        try:
                            result_data = json.loads(first_item.text)
                        except:
                            result_data = {"status": "success", "message": first_item.text}
                else:
                    result_data = {"status": "success", "message": str(first_item)}
            else:
                result_data = {"status": "success", "message": "Empty response"}


            logger.info("Project created successfully: %s for user: %s", project_data.get("name"), state["user_id"])

            state["project_result"]=result
            state["current_step"]="project"
            state["error"]=None
            return state
        
        except Exception as e:
            error_msg = f"Business creation failed: {e}"
            logger.error(error_msg)
            state["error"]=error_msg
            return state
        
    async def show_embedding_node(self, EmbeddedSignupUrlState) -> EmbeddedSignupUrlState:
        """inpute node of the project data."""

        return {"business_profile":EmbeddedSignupUrlState}
    

    async def create_embedding_node(self, state: OnboardingState) -> Dict[str, Any]:
        """
        Step 3: Embedded signup URL creation.
        Expects: embedded_signup data from frontend (after project completed)
        Returns: embedded_signup_result, marks workflow as 'completed'
        """
        if state.get("error"):
            return f"Sorry, an error occurred in creating project couldn't proceed: {state['error']}"
        
        create_embedding_tool =_current_mcp_tools["embedded_signup"]
        
        if not create_embedding_tool:
            return {"error": "generate_embedded_signup_url tool not found"}
        
        if not state.get("embedded_signup"):
            return {"error": "embedded_signup data not provided"}
        
        try:
            embedding_data = state["embedded_signup"]
            
            result = await create_embedding_tool.ainvoke(embedding_data)
            
            if hasattr(result, 'content'):
                result_data = result.content
            else:
                result_data = result

  
            if isinstance(result_data, str):
                try:
                    result_data = json.loads(result_data)
                except:
                    result_data = {"status": "success", "message": result_data}


            if isinstance(result_data, list):
                if len(result_data) > 0:
                    first_item = result_data[0]
                    
                    if isinstance(first_item, dict):
                        if first_item.get('type') == 'text' and 'text' in first_item:
                            text_content = first_item['text']
                            try:
                                result_data = json.loads(text_content)
                            except:
                                result_data = {"status": "success", "message": text_content}
                        else:
                            result_data = first_item
                    elif hasattr(first_item, 'text'):
                        try:
                            result_data = json.loads(first_item.text)
                        except:
                            result_data = {"status": "success", "message": first_item.text}
                else:
                    result_data = {"status": "success", "message": str(first_item)}
            else:
                result_data = {"status": "success", "message": "Empty response"}


            logger.info("Embedded signup URL created successfully for: %s", 
                        embedding_data.get("business_name"))
            
            state["embedded_signup_result"]=result
            state["current_step"]="embedded_signup"
            return state
        except Exception as e:
            error_msg = f"Embedded URL creation failed: {e}"
            logger.error(error_msg)
            state["error"]=error_msg
            return state
        


    def should_continue(self, state: OnboardingState) -> str:
        """Route based on error state."""
        if state.get("error"):
            return "handle_error"
        return "continue"

    async def handle_error_node(self, state: OnboardingState) -> Dict[str, Any]:
        """Error handling node."""
        error = state.get("error", "Unknown error occurred")
        logger.error("Workflow error: %s", error)
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


async def run_onboarding_http_workflow(
    user_id: str,
    current_step: Literal["business_profile", "project", "embedded_signup", "completed"],
    business_profile: Optional[CreateBusinessProfileState],
    project: Optional[CreateProjectState],
    embedded_signup: Optional[EmbeddedSignupUrlState]) -> Dict[str, Any]:
    """
    Execute the onboarding workflow with given initial state and MCP tools.
    Args:
        initial_state (OnboardingState): Initial state for the workflow.
        mcp_tools (Dict[str, Any]): MCP tools required for the workflow steps.
        
    Returns:
        Dict[str, Any]: Final state after workflow execution.
    """
    client = MultiServerMCPClient({
        "FormsMCP": {
            "url": "http://127.0.0.1:8000/mcp",
            "transport": "streamable-http"
        }})
    
    global _current_mcp_tools
    async with client.session("FormsMCP") as session:
        mcp_tools_list = await load_mcp_tools(session)
        mcp_tools = {t.name: t for t in mcp_tools_list}

        # Store tools in global variable (NOT in state - they can't be serialized)
        _current_mcp_tools = mcp_tools

        print(f"Loaded MCP tools: {list(mcp_tools.keys())}\n")

        OnboardingFlow_instance = OnboardingFlow()

        # Build and run workflow
        workflow = OnboardingFlow_instance.build_workflow()
        
        initial_state: OnboardingState = {
            "user_id": user_id,
            current_step:None,
            "business_profile": business_profile,
            "project": project,
            "embedded_signup": embedded_signup,
            "business_profile_result": "",
            "project_result": {},
            "embedded_signup_result": "",
            "error": ""}
        
        result = await workflow.ainvoke(initial_state)
        
        _current_mcp_tools = {}

        return {
            "business_profile_result": result["business_profile_result"],
            "project_result": result["project_result"],
            "embedded_signup_result": result["embedded_signup_result"],
            "error": result["error"]
        }



