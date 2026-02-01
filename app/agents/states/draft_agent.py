#This state of Drafting agent
from typing import TypedDict, Literal

#This state of SupervisorAgent
class SupervisorState(TypedDict):
    messages: list
    NEXT_AGENT: str
    SUB_AGENTS:Literal["Client_Intake_Agent","Legal_Research_Agent",
                       "Document_Classification_Agent",
                       "Drafting_Engine_Agent",
                       "Citation_Compliance_Agent",
                       "Review_Quality_Agent",
                       "Localization_Agent"]
    CURRENT_AGENT_STATUS:str
    INTAKE:str
    CLASSIFICATION:str
    RESEARCH:str
    DRAFTING:str
    CITATION_CHECK:str
    QUALITY_REVIEW:str
    LOCALIZATION:str
    HUMAN_REVIEW:str
    COMPLETE:str
    ERROR:str


    




