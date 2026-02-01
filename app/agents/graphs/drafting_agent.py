#This multi agent for the Drafting  Agent

#The Supervisor Agent orchestrates the entire drafting workflow, routing tasks to appropriate specialized agents, managing state, handling errors, and ensuring quality gates are met before final output.

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Literal
from ...services import openai_model
from ..states.draft_agent import SupervisorState
from ..prompts.drafting_agent import SUPERVISOR_PROMPT



def supervisor(state: SupervisorState):
    response = openai_model.invoke([
        {"role": "system", "content": SUPERVISOR_PROMPT},
        *state["messages"]
    ])
    return {"next_agent": response.content.strip().lower()}





