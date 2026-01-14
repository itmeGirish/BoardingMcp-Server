"""
Agent with MCP Workflow - HTTP Stateful

Imports the fixed-path workflow and exposes it as a tool.
Uses HTTP Stateful for best performance.
"""

import asyncio
import nest_asyncio
from typing import Dict, TypedDict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
import os
from dotenv import load_dotenv
from typing import Optional

nest_asyncio.apply()

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0)

class formState(TypedDict):
    name: str
    email: str
    mobile: str
    full_name: str
    position_applied: str
    years_of_experience: int
    skills: str
    resume_url: Optional[str]
    cover_letter: Optional[str]
    login_status: str  # "success" or "failure"
    login_result: Dict[str, Any]  # Full MCP result
    job_application_status: str  # "success" or "failure"
    job_application_result: Dict[str, Any]  # Full MCP result


# Global variable to hold MCP tools during workflow execution
# This avoids storing non-serializable tools in state
_current_mcp_tools: Dict[str, Any] = {}






async def node_login(state: formState) -> formState:
    """Call MCP login_user tool"""
    import json
    global _current_mcp_tools
    login_user = _current_mcp_tools["login_user"]

    display_name: str
    email: str
    company: str
    contact: str
    timezone: str
    currency: str
    company_size: str
    password: str
    user_id: str
    onboarding_id: str
    
    result = await login_user.ainvoke({
        "display_name": state["name"],
        "email": state["email"],
        "mobile": state["mobile"]
    })

    # Parse result - MCP tools return content as string or dict
    print(f"Login result type: {type(result)}")
    print(f"Login result: {result}")

    # Handle different result formats
    if hasattr(result, 'content'):
        result_data = result.content
    else:
        result_data = result

    # If result is a string (JSON), parse it
    if isinstance(result_data, str):
        try:
            result_data = json.loads(result_data)
        except:
            result_data = {"status": "success", "message": result_data}

    # Handle list results (MCP tools may return a list of content items)
    if isinstance(result_data, list):
        # Extract the first item if it's a list, or combine all text content
        if len(result_data) > 0:
            first_item = result_data[0]
            if isinstance(first_item, dict):
                # MCP returns {'type': 'text', 'text': '...'} format
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

    state["login_status"] = result_data.get("status", "success") if isinstance(result_data, dict) else "success"
    state["login_result"] = result_data if isinstance(result_data, dict) else {"status": "success", "message": str(result_data)}
    print(f"Login status: {state['login_status']}")
    return state


async def node_submit_job_application(state: formState) -> formState:
    """Call MCP submit_job_application tool"""
    global _current_mcp_tools
    submit_job = _current_mcp_tools["submit_job_application"]
    result = await submit_job.ainvoke({
        "full_name": state["full_name"],
        "email": state["email"],
        "mobile": state["mobile"],
        "position_applied": state["position_applied"],
        "years_of_experience": state["years_of_experience"],
        "skills": state["skills"],
        "resume_url": state["resume_url"],
        "cover_letter": state["cover_letter"]
    })

    # Parse result
    print(f"Job application result type: {type(result)}")
    print(f"Job application result: {result}")

    # Handle different result formats
    if hasattr(result, 'content'):
        result_data = result.content
    else:
        result_data = result

    # If result is a string (JSON), parse it
    if isinstance(result_data, str):
        import json
        try:
            result_data = json.loads(result_data)
        except:
            result_data = {"status": "success", "message": result_data}

    # Handle list results (MCP tools may return a list of content items)
    if isinstance(result_data, list):
        # Extract the first item if it's a list, or combine all text content
        if len(result_data) > 0:
            first_item = result_data[0]
            if isinstance(first_item, dict):
                # MCP returns {'type': 'text', 'text': '...'} format
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

    state["job_application_status"] = result_data.get("status", "success") if isinstance(result_data, dict) else "success"
    state["job_application_result"] = result_data if isinstance(result_data, dict) else {"status": "success", "message": str(result_data)}
    print(f"Job application status: {state['job_application_status']}")
    return state




def build_workflow():
    """
    FIXED PATH WORKFLOW:
    START → node_login → node_submit_job_application → END

    No LLM decides the order. Guaranteed sequence.
    """
    builder = StateGraph(formState)

    builder.add_node("node_login", node_login)
    builder.add_node("node_submit_job_application", node_submit_job_application)
    
    builder.add_edge(START, "node_login")
    builder.add_edge("node_login", "node_submit_job_application")
    builder.add_edge("node_submit_job_application", END)
    
    return builder.compile()


# ===========================================
# Run Workflow with HTTP Stateful
# ===========================================

async def run_workflow_http_stateful(
    name: str,
    email: str,
    mobile: str,
    full_name: str,
    position_applied: str,
    years_of_experience: int,
    skills: str,
    resume_url: Optional[str] = None,
    cover_letter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the fixed-path workflow using HTTP Stateful transport.

    Performance:
    - Connect: ~14ms
    - Per tool call: ~14ms
    - Total workflow: ~70ms
    """

    print("=== MCP Workflow (HTTP Stateful) ===\n")
    print("Connecting to MCP HTTP server...")

    client = MultiServerMCPClient({
        "FormsMCP": {
            "url": "http://127.0.0.1:8000/mcp",
            "transport": "streamable-http"
        }
    })

    # HTTP Stateful: persistent session
    global _current_mcp_tools
    async with client.session("FormsMCP") as session:
        mcp_tools_list = await load_mcp_tools(session)
        mcp_tools = {t.name: t for t in mcp_tools_list}

        # Store tools in global variable (NOT in state - they can't be serialized)
        _current_mcp_tools = mcp_tools

        print(f"Loaded MCP tools: {list(mcp_tools.keys())}\n")

        # Build and run workflow
        workflow = build_workflow()

        initial_state: formState = {
            "name": name,
            "email": email,
            "mobile": mobile,
            "full_name": full_name,
            "position_applied": position_applied,
            "years_of_experience": years_of_experience,
            "skills": skills,
            "resume_url": resume_url,
            "cover_letter": cover_letter,
            "login_status": "",
            "login_result": {},
            "job_application_status": "",
            "job_application_result": {}
        }

        result = await workflow.ainvoke(initial_state)

        # Clear global tools after workflow completes
        _current_mcp_tools = {}

        print("\n" + "=" * 40)
        print("Final Results:")
        print(f"  Login Status: {result['login_status']}")
        print(f"  Login Result: {result['login_result']}")
        print(f"  Job Application Status: {result['job_application_status']}")
        print(f"  Job Application Result: {result['job_application_result']}")

        return {
            "login_status": result["login_status"],
            "login_result": result["login_result"],
            "job_application_status": result["job_application_status"],
            "job_application_result": result["job_application_result"]
        }


# ===========================================
# Workflow as Tool for Agent
# ===========================================

@tool
def job_application_workflow_tool(
    name: str,
    email: str,
    mobile: str,
    full_name: str,
    position_applied: str,
    years_of_experience: int,
    skills: str,
    resume_url: Optional[str] = None,
    cover_letter: Optional[str] = None
) -> str:
    """
    when user ask for job application follow this flow
    A job application workflow that:
    1. Connects to MCP server (HTTP Stateful - fastest)
    2. Process user login information after form submission.
    3. Submits a job application with all provided details

    This is a FIXED PATH workflow - order is guaranteed, no LLM decides.

    Returns a string message with the workflow result.
    """
    result = asyncio.run(run_workflow_http_stateful(
        name=name,
        email=email,
        mobile=mobile,
        full_name=full_name,
        position_applied=position_applied,
        years_of_experience=years_of_experience,
        skills=skills,
        resume_url=resume_url,
        cover_letter=cover_letter
    ))

    # Convert dict result to string (CopilotKit/LangGraph tools must return strings)
    login_status = result.get("login_status", "unknown")
    job_status = result.get("job_application_status", "unknown")

    return f"""Job application workflow completed!

✅ Login Status: {login_status}
   User: {name} ({email}, {mobile})

✅ Application Status: {job_status}
   Position: {position_applied}
   Applicant: {full_name}
   Experience: {years_of_experience} years
   Skills: {skills}
   Resume: {resume_url if resume_url else 'Not provided'}
   Cover Letter: {'Provided' if cover_letter else 'Not provided'}

Your application has been received and is being processed. We will contact you at {email} with updates."""



