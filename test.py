# from langchain_community.chat_models import ChatOllama

# ollma_model = ChatOllama(
#     model="kimi-k2.5:cloud",
#     temperature=1,
# )

from typing import List

from langchain.messages import AIMessage
from langchain.tools import tool
from langchain_ollama import ChatOllama


# @tool
# def validate_user(user_id: int, addresses: List[str]) -> bool:
#     """Validate user using historical addresses.

#     Args:
#         user_id (int): the user ID.
#         addresses (List[str]): Previous addresses as a list of strings.
#     """
#     return True


llm = ChatOllama(
    model="kimi-k2.5:cloud",
    validate_model_on_init=True,
    temperature=1,
    top_p=0.95
)

result = llm.invoke(
"""
Draft a petition under Section 482 CrPC for Madras High Court to quash FIR under IPC 406 and 420.
Facts: It is a supply agreement dispute. Petitioner received advance money but delivery got delayed due to raw material shortage and port delay. Petitioner was continuously communicating and had no dishonest intention. Respondent wrongly filed FIR to convert civil dispute into criminal case.
Include: cause title, memo of parties, list of dates, synopsis, grounds, prayer.
Mention that ingredients of 406 and 420 are not made out, dispute is civil in nature, and FIR is abuse of process. Use proper legal drafting format.
"""
)

print(result.content)
