"""
This is the main entry point for the agent.
"""

from typing import List
from copilotkit import CopilotKitState
from langchain.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
import asyncio
import nest_asyncio
import concurrent.futures
import json

nest_asyncio.apply()


_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

class AgentState(CopilotKitState):
    proverbs: List[str]

    


