
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# 0) Pydantic Models (Structured Outputs)
# -------------------------------------------------------------------

Lang = Literal["en", "hi", "kn"]
Tone = Literal["formal", "neutral"]
RiskLevel = Literal["low", "med", "high"]
law_domain=Literal["Civil", "Criminal", "Family", "Corporate", "IP", "Other"]
SlotSource = Literal["user_text", "evidence", "assumed", "inferred"]
SlotType = Literal["string", "date", "number", "bool", "list", "object"]



class Party(BaseModel):
    name: Optional[str] = None
    age: Optional[str] = None
    occupation: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None


class Parties(BaseModel):
    primary: Party = Field(default_factory=Party)
    opposite: List[Party] = Field(default_factory=list)


class Jurisdiction(BaseModel):
    country: str = "India"
    state: Optional[str] = None
    city: Optional[str] = None
    court_type: Optional[str] = None
    place: Optional[str] = None


class Amounts(BaseModel):
    principal: Optional[float] = None
    interest_rate: Optional[float] = None
    damages: Optional[float] = None


class ChronologyItem(BaseModel):
    date: Optional[str] = None  # keep string for simplicity ("YYYY-MM-DD" or "DD/MM/YYYY")
    event: str
    source: SlotSource = "user_text"
    confidence: float = 0.8


class Facts(BaseModel):
    summary: str = ""
    chronology: List[ChronologyItem] = Field(default_factory=list)
    amounts: Amounts = Field(default_factory=Amounts)
    cause_of_action_date: Optional[str] = None


class EvidenceItem(BaseModel):
    type: str  # e.g., "bank_transfer", "whatsapp_chat", "notice"
    description: str
    relevance: Optional[str] = None
    ref: Optional[str] = None  # optional UTR / filename / exhibit id


class Slot(BaseModel):
    key: str
    value: Any
    type: SlotType = "string"
    source: SlotSource = "user_text"
    confidence: float = 0.7


class DynamicFields(BaseModel):
    slots: List[Slot] = Field(default_factory=list)
    field_sources: Dict[str, Any] = Field(default_factory=dict)


class Classification(BaseModel):
    topics: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = "low"
    missing_fields: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class RagPlan(BaseModel):
    collections: List[str] = Field(default_factory=list)
    queries: List[str] = Field(default_factory=list)
    top_k: int = 8
    filters: Dict[str, Any] = Field(default_factory=dict)


class RagSource(BaseModel):
    collection: Optional[str] = None
    book: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    topic: Optional[str] = None
    year: Optional[int] = None


class RagChunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    source: RagSource


class RagRule(BaseModel):
    rule: str
    support: List[str] = Field(default_factory=list)


class RagBundle(BaseModel):
    domain: Optional[str] = None
    queries: List[str] = Field(default_factory=list)
    chunks: List[RagChunk] = Field(default_factory=list)
    authority_map: Dict[str, List[str]] = Field(default_factory=dict)
    rules: List[RagRule] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    raw_context: str = ""


class PlaceholderUsed(BaseModel):
    key: str
    reason: str


class DraftArtifact(BaseModel):
    doc_type: str
    title: str
    text: str
    placeholders_used: List[PlaceholderUsed] = Field(default_factory=list)
    citations_used: List[str] = Field(default_factory=list)


class ReviewIssue(BaseModel):
    issue: str
    fix: str
    location: str
    severity: Literal["legal", "formatting"] = "legal"


class UnsupportedStatement(BaseModel):
    statement: str
    reason: str
    location: Optional[str] = None


class Review(BaseModel):
    review_pass: bool
    blocking_issues: List[ReviewIssue] = Field(default_factory=list)
    non_blocking_issues: List[ReviewIssue] = Field(default_factory=list)
    unsupported_statements: List[UnsupportedStatement] = Field(default_factory=list)
    final_artifacts: List[DraftArtifact] = Field(default_factory=list)


class Meta(BaseModel):
    language: Lang = "en"
    tone: Tone = "formal"
    run_mode: Literal["one_shot"] = "one_shot"


# Node outputs
class IntakeNode(BaseModel):
    facts: Facts
    jurisdiction: Jurisdiction
    parties: Parties
    evidence: List[EvidenceItem] = Field(default_factory=list)
    dynamic_fields: DynamicFields = Field(default_factory=DynamicFields)
    classification: Classification = Field(default_factory=Classification)



class ClassifyNode(BaseModel):
    law_domain: Literal["Civil", "Criminal", "Family", "Corporate", "IP", "Other"]
    doc_type: str
    cause_type: str = ""
    classification: Classification
    rag_plan: RagPlan


class IntakeClassifyNode(BaseModel):
    """Merged intake + classify in ONE LLM call (saves ~10s)."""
    # Intake fields
    facts: Facts
    jurisdiction: Jurisdiction
    parties: Parties
    evidence: List[EvidenceItem] = Field(default_factory=list)
    dynamic_fields: DynamicFields = Field(default_factory=DynamicFields)
    # Classify fields
    law_domain: Literal["Civil", "Criminal", "Family", "Corporate", "IP", "Other"]
    doc_type: str
    cause_type: str = ""
    classification: Classification
    rag_plan: RagPlan


class DraftNode(BaseModel):
    draft_artifacts: List[DraftArtifact]


class ReviewNode(BaseModel):
    review: Review


CivilFamily = Literal[
    "money_and_debt",
    "contract_and_commercial",
    "immovable_property",
    "injunction_and_declaratory",
    "tort_and_civil_wrong",
    "tenancy_and_rent",
    "partnership_and_business",
    "ip_civil",
    "trust_and_fiduciary",
    "execution_and_restitution",
    "special_and_miscellaneous",
    "succession_and_estate",
    "unsupported",
]

CivilDecisionStatus = Literal["not_applicable", "resolved", "ambiguous", "unsupported"]
CivilDraftStrategy = Literal["template_first", "free_text"]


class CivilDecision(BaseModel):
    enabled: bool = False
    family: Optional[CivilFamily] = None
    original_cause_type: Optional[str] = None
    resolved_cause_type: Optional[str] = None
    relationship_track: Optional[str] = None
    status: CivilDecisionStatus = "not_applicable"
    draft_strategy: CivilDraftStrategy = "free_text"
    template_eligible: bool = False
    maintainability_checks: List[str] = Field(default_factory=list)
    ambiguity_flags: List[str] = Field(default_factory=list)
    blocking_issues: List[str] = Field(default_factory=list)
    limitation: Dict[str, Any] = Field(default_factory=dict)
    allowed_statutes: List[str] = Field(default_factory=list)
    forbidden_statutes: List[str] = Field(default_factory=list)
    allowed_reliefs: List[str] = Field(default_factory=list)
    forbidden_reliefs: List[str] = Field(default_factory=list)
    allowed_damages: List[str] = Field(default_factory=list)
    forbidden_damages: List[str] = Field(default_factory=list)
    allowed_doctrines: List[str] = Field(default_factory=list)
    forbidden_doctrines: List[str] = Field(default_factory=list)
    filtered_red_flags: List[str] = Field(default_factory=list)
    route_reason: str = ""
    confidence: float = 0.0


class DomainDecision(BaseModel):
    enabled: bool = False
    plugin_key: Optional[str] = None
    law_domain: Optional[str] = None
    family: Optional[str] = None
    subtype: Optional[str] = None
    relationship_track: Optional[str] = None
    status: CivilDecisionStatus = "not_applicable"
    draft_strategy: CivilDraftStrategy = "free_text"
    template_eligible: bool = False
    maintainability_checks: List[str] = Field(default_factory=list)
    ambiguity_flags: List[str] = Field(default_factory=list)
    blocking_issues: List[str] = Field(default_factory=list)
    limitation: Dict[str, Any] = Field(default_factory=dict)
    allowed_statutes: List[str] = Field(default_factory=list)
    forbidden_statutes: List[str] = Field(default_factory=list)
    allowed_reliefs: List[str] = Field(default_factory=list)
    forbidden_reliefs: List[str] = Field(default_factory=list)
    allowed_damages: List[str] = Field(default_factory=list)
    forbidden_damages: List[str] = Field(default_factory=list)
    allowed_doctrines: List[str] = Field(default_factory=list)
    forbidden_doctrines: List[str] = Field(default_factory=list)
    filtered_red_flags: List[str] = Field(default_factory=list)
    route_reason: str = ""
    confidence: float = 0.0


class DraftPlanIR(BaseModel):
    plugin_key: Optional[str] = None
    law_domain: Optional[str] = None
    family: Optional[str] = None
    subtype: Optional[str] = None
    relationship_track: Optional[str] = None
    route_reason: str = ""
    required_sections: List[str] = Field(default_factory=list)
    required_reliefs: List[str] = Field(default_factory=list)
    optional_reliefs: List[str] = Field(default_factory=list)
    required_averments: List[str] = Field(default_factory=list)
    mandatory_inline_sections: List[Dict[str, Any]] = Field(default_factory=list)
    maintainability_checks: List[str] = Field(default_factory=list)
    limitation: Dict[str, Any] = Field(default_factory=dict)
    verified_provisions: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_checklist: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------------
# 1) LangGraph State (TypedDict) — single global state for ALL doc types
# -------------------------------------------------------------------

class DraftingState(TypedDict, total=False):
    user_request: str

    intake: IntakeNode | None
    classify: ClassifyNode | None
    domain_plugin: str | None
    decision_ir: DomainDecision | None
    plan_ir: DraftPlanIR | None
    domain_gate_issues: List[Dict[str, Any]]
    civil_decision: CivilDecision | None
    civil_draft_plan: Dict[str, Any] | None
    civil_gate_issues: List[Dict[str, Any]]
    rag: RagBundle | None
    court_fee: Dict[str, Any] | None       # web search: jurisdiction court fee rates
    legal_research: Dict[str, Any] | None  # web search: limitation period + procedural requirements
    mandatory_provisions: Dict[str, Any] | None  # enrichment node: limitation + user-cited provisions
    lkb_brief: Dict[str, Any] | None  # LKB: structured legal brief from knowledge base

    # Template-first pipeline fields (v3.0)
    template: Dict[str, Any] | None         # loaded template JSON from template_loader
    claim_ledger: List[Dict[str, Any]]      # aggregated claims from all sections

    # Shared pipeline fields (v3.0 + v4.0)
    filled_sections: Dict[str, str] | List[Dict[str, Any]]  # v4.0: {section_id: text} | v3.0: [{section_id, text, ...}]
    postprocess_issues: List[Dict[str, Any]]  # issues found/fixed by postprocess
    postprocess_light: bool                  # True = light postprocess after section_fixer

    # v4.0 exemplar-guided pipeline fields
    structural_issues: List[Dict[str, Any]]  # structural_gate: missing section checks
    citation_issues: List[Dict[str, Any]]    # citation_validator: unverified citations
    evidence_anchoring_issues: List[Dict[str, Any]]  # evidence_anchoring: replaced tokens + quality
    accuracy_gate_issues: List[Dict[str, Any]]  # v10.0 accuracy gates: procedural, date, arithmetic, annexure, rules

    draft: DraftNode | None
    final_draft: DraftNode | None
    review: ReviewNode | None

    review_count: int  # number of review cycles completed; caps re-draft loop

    meta: Dict[str, Any]
    errors: List[str]
