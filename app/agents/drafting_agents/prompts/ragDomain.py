RAG_PROMPT = """
Build a focused legal retrieval query for drafting support.

Document Type: {doc_type}
Law Domain: {law_domain}
Classification: {classification}
RAG Plan: {rag_plan}
"""

RAG_USER_PROMPT = """
Return a concise retrieval intent with key legal terms and authorities to fetch.
"""
