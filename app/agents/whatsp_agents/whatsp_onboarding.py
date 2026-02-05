# ONLY this file imports everything:
from functools import partial
from .graphs.whsp_onboarding_agent import create_graph
from .states.whsp_onboarding_agent import OnboardingAgentState
from .prompts.whsp_onboarding_agent import ONBOARDING_SYSTEM_PROMPT
from .tools.whsp_onboarding_agent import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from .nodes.whsp_onboarding_agent import call_model_node




# Wires everything together:
def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=ONBOARDING_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES        # From tools.py
    )

def _assemble_graph():
    return create_graph(
        state_class=OnboardingAgentState,         # From states.py
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS                       # From tools.py
    )

# Create singleton
onboarding_graph = _assemble_graph()
