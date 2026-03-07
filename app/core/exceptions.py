# ──────────────────────────────────────────────────────────────────────────────
# Custom exceptions for the AIFBuddy application.
# All domain-specific exceptions are defined here and exported via core/__init__.py
# ──────────────────────────────────────────────────────────────────────────────


# ── Vector store ───────────────────────────────────────────────────────────────

class vectorStorCreationError(Exception):
    """Raised when vector store creation fails."""
    def __init__(self, message="An error occurred while creating the vector store."):
        self.message = message
        super().__init__(self.message)


class VectorstoreDeletionError(Exception):
    """Raised when vector store deletion fails."""
    def __init__(self, message="An error occurred while deleting the vector store."):
        self.message = message
        super().__init__(self.message)


class PayloadinsertionError(Exception):
    """Raised when payload insertion into the vector store fails."""
    def __init__(self, message="An error occurred while inserting the payload into the vector store."):
        self.message = message
        super().__init__(self.message)


class EmbeddingRetrievalError(Exception):
    """Raised when embedding retrieval fails."""
    def __init__(self, message="An error occurred while retrieving embeddings."):
        self.message = message
        super().__init__(self.message)


# ── LangGraph node execution ───────────────────────────────────────────────────

class GenerateNodeExecutionError(Exception):
    """Raised when the generate_query_or_respond node fails."""
    def __init__(self, message="An error occurred during the generation node execution."):
        self.message = message
        super().__init__(self.message)


class Grade_DocumentsNodeExecutionError(Exception):
    """Raised when the grade_documents node fails."""
    def __init__(self, message="An error occurred during the grading documents node execution."):
        self.message = message
        super().__init__(self.message)


class Rewrite_QuestionNodeExecutionError(Exception):
    """Raised when the rewrite_question node fails."""
    def __init__(self, message="An error occurred during the rewriting question node execution."):
        self.message = message
        super().__init__(self.message)


class GenerateanswerToolExecutionError(Exception):
    """Raised when the generate_answer node fails."""
    def __init__(self, message="An error occurred during the generate answer tool execution."):
        self.message = message
        super().__init__(self.message)


# ── Agent tools ────────────────────────────────────────────────────────────────

class QuadrantRAGToolExecutionError(Exception):
    """Raised when QuadrantRAGTool fails."""
    def __init__(self, message="An error occurred during the Quadrant RAG Tool execution."):
        self.message = message
        super().__init__(self.message)


class AvailabLeModulesToolExecutionError(Exception):
    """Raised when AvailabLeModulesTool fails."""
    def __init__(self, message="An error occurred while fetching available modules."):
        self.message = message
        super().__init__(self.message)


class AvailabLeInsightsToolExecutionError(Exception):
    """Raised when AvailabLeInsightsTool fails."""
    def __init__(self, message="An error occurred while fetching available insights."):
        self.message = message
        super().__init__(self.message)


# ── Session management ─────────────────────────────────────────────────────────

class SessionCreationError(Exception):
    """Raised when a new session cannot be created."""
    def __init__(self, message="An error occurred while creating the session."):
        self.message = message
        super().__init__(self.message)


class UnauthorizedSessionError(Exception):
    """Raised when a user attempts to access a session they do not own."""
    def __init__(self, message="Unauthorized access to session."):
        self.message = message
        super().__init__(self.message)


class SessionNotFoundError(Exception):
    """Raised when a requested session does not exist."""
    def __init__(self, message="Session not found."):
        self.message = message
        super().__init__(self.message)


# ── Database ───────────────────────────────────────────────────────────────────

class DatabaseConnectionError(Exception):
    """Raised when the database connection cannot be established."""
    def __init__(self, message="Failed to connect to the database."):
        self.message = message
        super().__init__(self.message)


class ChatHistorySaveError(Exception):
    """Raised when saving chat history messages fails."""
    def __init__(self, message="An error occurred while saving chat history."):
        self.message = message
        super().__init__(self.message)


class CheckpointSaveError(Exception):
    """Raised when writing a LangGraph checkpoint to the database fails."""
    def __init__(self, message="An error occurred while saving the checkpoint."):
        self.message = message
        super().__init__(self.message)


class CheckpointLoadError(Exception):
    """Raised when loading a LangGraph checkpoint from the database fails."""
    def __init__(self, message="An error occurred while loading the checkpoint."):
        self.message = message
        super().__init__(self.message)


# ── Services ───────────────────────────────────────────────────────────────────

class LLMServiceError(Exception):
    """Raised when the LLM service (Azure OpenAI / Groq) returns an error."""
    def __init__(self, message="An error occurred in the LLM service."):
        self.message = message
        super().__init__(self.message)


class MonitoringServiceError(Exception):
    """Raised when the Langfuse monitoring service fails."""
    def __init__(self, message="An error occurred in the monitoring service."):
        self.message = message
        super().__init__(self.message)


# ── Streaming / API ────────────────────────────────────────────────────────────

class StreamingError(Exception):
    """Raised when an SSE stream fails during generation."""
    def __init__(self, message="An error occurred during response streaming."):
        self.message = message
        super().__init__(self.message)


class RateLimitExceededError(Exception):
    """Raised when a user exceeds the configured rate limit."""
    def __init__(self, message="Rate limit exceeded. Please try again later."):
        self.message = message
        super().__init__(self.message)