"""Pydantic models for the frozen data contract (PLAN.md section 5) and API contract (section 6).

Do not change field names or enum values here without editing PLAN.md and telling both devs.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- enums

Mode = Literal["live", "demo"]
DocType = Literal["after_visit_summary", "clinical_note"]
InstructionKind = Literal["medication", "follow_up", "lab", "lifestyle", "warning_sign", "supply"]
Action = Literal["start", "continue", "stop", "avoid", "change"]
ConflictType = Literal[
    "dose_mismatch", "frequency_mismatch", "action_mismatch", "date_mismatch", "duration_mismatch"
]
ConflictLevel = Literal["confirmed_conflict", "potential_conflict", "insufficient_data"]
TaskStatus = Literal["open", "patient_reported_done", "needs_clarification", "unknown"]
Language = Literal["en", "es"]
Detail = Literal["brief", "detailed"]
LearnMode = Literal["read", "listen", "visual"]
Style = Literal["brief", "detailed", "analogy", "audio", "visual"]
STYLES: list[str] = ["brief", "detailed", "analogy", "audio", "visual"]

LABELS: list[str] = [
    "understood", "dose_error", "frequency_error", "duration_error", "stop_negation",
    "followup_timing_error", "uncertain", "source_conflict",
    "side_effect", "cost", "ran_out_refill", "forgot", "schedule_conflict",
    "doesnt_see_importance", "confusion", "wants_to_stop",
]

SYNTHETIC_BANNER = "SYNTHETIC DEMO RECORD — NOT A REAL PATIENT"

# ---------------------------------------------------------------- CarePlan


class Evidence(BaseModel):
    document_id: str
    quote: str


class Document(BaseModel):
    id: str
    type: DocType
    title: str
    text: str


class Instruction(BaseModel):
    id: str
    kind: InstructionKind
    medication_name: Optional[str] = None
    strength: Optional[str] = None
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency_per_day: Optional[int] = None
    duration: Optional[str] = None
    action: Optional[Action] = None
    refills: Optional[int] = None
    quantity: Optional[str] = None
    due: Optional[str] = None
    evidence: Evidence


class Conflict(BaseModel):
    id: str
    type: ConflictType
    instruction_ids: list[str]
    level: ConflictLevel
    resolved: bool = False


class Task(BaseModel):
    id: str
    instruction_id: str
    label: str
    status: TaskStatus = "open"


class CarePlan(BaseModel):
    case_id: str
    synthetic: bool = True
    documents: list[Document]
    instructions: list[Instruction]
    conflicts: list[Conflict] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)


class CarePlanResponse(CarePlan):
    mode: Mode = "demo"


# ---------------------------------------------------------------- PatientProfile


def _default_bandit() -> dict[str, list[float]]:
    return {s: [1.0, 1.0] for s in STYLES}


class Concern(BaseModel):
    """A concern in the patient's own words. Patient-owned: visible, editable, deletable."""
    id: str
    text: str
    labels: list[str] = Field(default_factory=list)
    confirmed: bool = False


class PatientProfile(BaseModel):
    profile_id: str
    language: Language = "en"
    detail: Detail = "brief"
    modes: list[LearnMode] = Field(default_factory=lambda: ["read"])
    context_opt_in: Optional[str] = None
    term_scores: dict[str, float] = Field(default_factory=dict)
    style_bandit: dict[str, list[float]] = Field(default_factory=_default_bandit)
    teach_back_history: list[dict] = Field(default_factory=list)
    concerns: list[Concern] = Field(default_factory=list)


class PatientProfileResponse(PatientProfile):
    mode: Mode = "demo"


class ProfilePatch(BaseModel):
    """Partial PatientProfile for POST /profile and PUT /profile/{id}."""
    profile_id: Optional[str] = None
    language: Optional[Language] = None
    detail: Optional[Detail] = None
    modes: Optional[list[LearnMode]] = None
    context_opt_in: Optional[str] = None
    term_scores: Optional[dict[str, float]] = None
    style_bandit: Optional[dict[str, list[float]]] = None
    concerns: Optional[list[Concern]] = None


# ---------------------------------------------------------------- requests / responses


class DemoCaseSummary(BaseModel):
    case_id: str
    title: str
    description: str
    mode: Mode = "demo"


class DocumentInput(BaseModel):
    text: str
    type_hint: Optional[DocType] = None


class CreateCaseRequest(BaseModel):
    documents: Optional[list[DocumentInput]] = None
    demo_case_id: Optional[str] = None


class Citation(BaseModel):
    document_id: str
    quote: str


class DefinedTerm(BaseModel):
    term: str
    definition: str


class FactCheck(BaseModel):
    passed: bool
    unsupported: list[str] = Field(default_factory=list)


class ExplainRequest(BaseModel):
    case_id: str
    profile_id: str
    instruction_id: str
    style_override: Optional[Style] = None


class ExplainResponse(BaseModel):
    text: str
    style: Style
    why_this_style: str
    defined_terms: list[DefinedTerm]
    citations: list[Citation]
    fact_check: FactCheck
    mode: Mode = "demo"


class AskRequest(BaseModel):
    case_id: str
    profile_id: str
    question: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    in_documents: bool
    urgent: bool
    mode: Mode = "demo"


class TeachbackRequest(BaseModel):
    case_id: str
    profile_id: str
    instruction_id: str
    response_text: str


SlotResult = Literal["correct", "incorrect", "not_mentioned", "not_documented", "documents_disagree"]


class SlotCheck(BaseModel):
    dose: SlotResult
    frequency: SlotResult
    duration: SlotResult


class TeachbackResponse(BaseModel):
    labels: list[str]
    confidence: float
    slot_check: SlotCheck
    source_conflict: bool
    feedback_text: str
    pathway: Literal["ml", "rules", "both"]
    mode: Mode = "demo"


class BarrierRequest(BaseModel):
    case_id: str
    profile_id: str
    text: str


class BarrierResponse(BaseModel):
    labels: list[str]
    confirm_prompt: str
    urgent: bool
    support_text: str
    example_id: str
    mode: Mode = "demo"


class FeedbackRequest(BaseModel):
    profile_id: str
    kind: Literal["thumbs", "term_tap", "style_change", "label_confirm", "label_correct"]
    payload: dict = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    profile: PatientProfile
    model_updated: bool
    mode: Mode = "demo"


class BriefingInclude(BaseModel):
    concerns: list[str] = Field(default_factory=list)   # concern ids (or raw text)
    conflicts: list[str] = Field(default_factory=list)  # conflict ids


class BriefingRequest(BaseModel):
    case_id: str
    profile_id: str
    include: BriefingInclude = Field(default_factory=BriefingInclude)


class BriefingResponse(BaseModel):
    draft_en: str
    draft_patient_language: str
    citations: list[Citation]
    mode: Mode = "demo"
