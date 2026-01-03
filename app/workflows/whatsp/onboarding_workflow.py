"""Onboarding workflow that loads the on mcp server tools """

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from typing import Dict, TypedDict, Any
from .state import Create_business_profileState,CreateProjectState,EmbeddedSignupUrlState
from dataclasses import dataclass


#Onboarding state
class OnboardingState(TypedDict):
    create_profile:Create_business_profileState
    create_busines:CreateProjectState
    create_embedding:EmbeddedSignupUrlState


@dataclass
class OnboardingFlow:
    mcp_tools: Dict[str, Any]
    user_id:str
    self.mcp_tools=mcp_tools
    self.user_id=user_id

    async create_business_node(businesState:Create_business_profileState):
        """ Business profile creation"""
        business_creation_tool=state["mcp_tools"]["create_business_profile"]
        result = await add_tool.ainvoke(businesState)
        return result

    async create_project_id_node(projectState:CreateProjectState):
        """Creating project for buisness"""
        create_project_tool=state["mcp_tools"]["create_project"]
        result = await add_tool.ainvoke(projectState)
        return result

    async create_embedding_url_node(embeddingState:EmbeddedSignupUrlState):
        """Create embedding url"""
        create_project_tool=state["mcp_tools"]["generate_embedded_signup_url"]
        result = await add_tool.ainvoke(EmbeddedSignupUrlState)
        return result

    def build_workflow():
        """This is fixed workflow
        FIXED PATH WORKFLOW:
    START → create_business_node → create_project_id_node → create_embedding_url_node → END
        
        """
        
        builder = StateGraph(OnboardingState)
        builder.add_node("create_business_node", create_business_node)
        builder.add_node("create_project_id_node", create_project_id_node)
        builder.add_node("create_embedding_url_node", create_embedding_url_node)

        builder.add_edge(START, "create_business_node")
        builder.add_edge("create_business_node", "create_project_id_node")
        builder.add_edge("create_project_id_node", "create_embedding_url_node")
        builder.add_edge("create_embedding_url_node", END)
        return builder.compile()





        













