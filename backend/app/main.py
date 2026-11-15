"""REXO FastAPI app. Routes follow the frozen API contract in PLAN.md section 6.

Every JSON response carries "mode": "live" | "demo". Phase 1 routes run on seeded
fixtures and deterministic rules, so they report "demo".
"""
from __future__ import annotations

import json
import os
import re

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import barrier, briefing, explain, ingest, learning, store, teachback
from .safety import is_urgent, urgent_message
from .schemas import (
    AskRequest, AskResponse, BarrierRequest, BarrierResponse, BriefingRequest, BriefingResponse,
    CarePlan, CarePlanResponse, Citation, Concern, CreateCaseRequest, DemoCaseSummary, Document,
    ExplainRequest, ExplainResponse, FactCheck, FeedbackRequest, FeedbackResponse, PatientProfile,
    PatientProfileResponse, ProfilePatch, TeachbackRequest, TeachbackResponse,
)

load_dotenv()

app = FastAPI(title="REXO API", version="0.1.0")
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
api = APIRouter(prefix="/api")


def _mode() -> str:
    # Phase 1: everything runs on fixtures + rules. Becomes "live" once extract.py /
    # explain.py actually call OpenAI with a configured key.
    return "demo"


def _case_or_404(case_id: str) -> CarePlan:
    plan = store.get_case(case_id)
    if not plan:
        raise HTTPException(404, f"Unknown case_id: {case_id}")
    return plan


def _instruction_or_404(plan: CarePlan, instruction_id: str):
    ins = next((i for i in plan.instructions if i.id == instruction_id), None)
    if not ins:
        raise HTTPException(404, f"Unknown instruction_id: {instruction_id}")
    return ins


def _profile_out(p: PatientProfile) -> PatientProfileResponse:
    return PatientProfileResponse(**p.model_dump(), mode=_mode())


# ---------------------------------------------------------------- health


@api.get("/health")
def health():
    return {"ok": True, "mode": _mode(),
            "openai_key": bool(os.getenv("OPENAI_API_KEY")),
            "deepgram_key": bool(os.getenv("DEEPGRAM_API_KEY"))}


# ---------------------------------------------------------------- cases


@api.get("/demo-cases", response_model=list[DemoCaseSummary])
def demo_cases():
    return [DemoCaseSummary(**c, mode=_mode()) for c in store.demo_cases()]


@api.post("/cases", response_model=CarePlanResponse)
def create_case(req: CreateCaseRequest):
    if req.demo_case_id:
        plan = store.demo_case_copy(req.demo_case_id)
        if not plan:
            raise HTTPException(404, f"Unknown demo_case_id: {req.demo_case_id}")
        return CarePlanResponse(**plan.model_dump(), mode=_mode())
    if not req.documents:
        raise HTTPException(422, "Provide either demo_case_id or documents.")

    texts = [d.text for d in req.documents]
    fixture = store.match_fixture_by_text(texts)
    case_id = store.new_case_id()
    if fixture:
        _, seeded = store.load_fixture(fixture)
        plan = seeded.model_copy(update={"case_id": case_id})
    else:
        # Phase 2: extract.py fills instructions from pasted text via OpenAI + quote verification.
        # Until then, pasted text is typed and redacted but no instructions are invented.
        documents = []
        counters = {"after_visit_summary": 0, "clinical_note": 0}
        for d in req.documents:
            dtype = ingest.classify_document(d.text, d.type_hint)
            counters[dtype] += 1
            prefix = "avs" if dtype == "after_visit_summary" else "note"
            text, _ = ingest.redact(d.text)
            documents.append(Document(id=f"{prefix}-{counters[dtype]}", type=dtype,
                                      title=ingest.default_title(dtype), text=text))
        plan = CarePlan(case_id=case_id, documents=documents, instructions=[], conflicts=[], tasks=[])
    store.save_case(plan)
    return CarePlanResponse(**plan.model_dump(), mode=_mode())


@api.get("/cases/{case_id}", response_model=CarePlanResponse)
def get_case(case_id: str):
    return CarePlanResponse(**_case_or_404(case_id).model_dump(), mode=_mode())


# ---------------------------------------------------------------- photo intake (P1 stretch)


@api.post("/ingest/photo")
async def ingest_photo(file: UploadFile = File(...)):
    raise HTTPException(501, "Photo intake is not available yet. Please paste the document text instead.")


# ---------------------------------------------------------------- profiles


def _apply_patch(p: PatientProfile, patch: ProfilePatch) -> PatientProfile:
    data = patch.model_dump(exclude_unset=True, exclude={"profile_id"})
    updated = p.model_copy(update=data)
    # Re-validate nested models after model_copy.
    return PatientProfile.model_validate(updated.model_dump())


@api.post("/profile", response_model=PatientProfileResponse)
def create_profile(patch: ProfilePatch):
    pid = patch.profile_id or store.new_profile_id()
    existing = store.get_profile(pid)
    p = _apply_patch(existing or PatientProfile(profile_id=pid), patch)
    if not existing and patch.style_bandit is None:
        learning.seed_from_onboarding(p)
    return _profile_out(store.save_profile(p))


@api.get("/profile/{profile_id}", response_model=PatientProfileResponse)
def get_profile(profile_id: str):
    p = store.get_profile(profile_id)
    if not p:
        raise HTTPException(404, f"Unknown profile_id: {profile_id}")
    return _profile_out(p)


@api.put("/profile/{profile_id}", response_model=PatientProfileResponse)
def update_profile(profile_id: str, patch: ProfilePatch):
    p = store.get_or_create_profile(profile_id)
    return _profile_out(store.save_profile(_apply_patch(p, patch)))


@api.post("/profile/{profile_id}/reset", response_model=PatientProfileResponse)
def reset_profile(profile_id: str):
    p = PatientProfile(profile_id=profile_id)
    learning.seed_from_onboarding(p)
    return _profile_out(store.save_profile(p))


# ---------------------------------------------------------------- explain / ask


@api.post("/explain", response_model=ExplainResponse)
def explain_route(req: ExplainRequest):
    plan = _case_or_404(req.case_id)
    ins = _instruction_or_404(plan, req.instruction_id)
    profile = store.get_or_create_profile(req.profile_id)
    if req.style_override:
        style = req.style_override
        why = ("Elegido por usted." if profile.language == "es" else "You chose this style.")
    else:
        style, why = learning.choose_style(profile)
    learning.remember_style(profile.profile_id, style)
    text, terms, citations, (passed, unsupported) = explain.explain(plan, ins, profile, style)
    return ExplainResponse(text=text, style=style, why_this_style=why, defined_terms=terms,
                           citations=citations, fact_check=FactCheck(passed=passed, unsupported=unsupported),
                           mode=_mode())


_KIND_WORDS = {
    "follow_up": r"follow|appointment|visit|come back|return|cita|seguimiento|regres|consulta",
    "lab": r"lab|blood test|test|panel|a1c|analisis|examen|prueba|sangre",
    "warning_sign": r"call|warning|emergency|worse|llamar|emergencia|peor|signos",
    "lifestyle": r"rub|press|avoid|frotar|tallar",
}


@api.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    plan = _case_or_404(req.case_id)
    profile = store.get_or_create_profile(req.profile_id)
    lang = profile.language
    if is_urgent(req.question):
        return AskResponse(answer=urgent_message(lang), citations=[], in_documents=False, urgent=True,
                           mode=_mode())
    from .reconcile import canonical_name, DRUG_CLASSES, conflicts_for
    from .safety import fold
    q = fold(req.question)
    hits = []
    for ins in plan.instructions:
        name = canonical_name(ins.medication_name)
        names = {name} | (DRUG_CLASSES.get(name, set()) if name else set())
        if ins.kind == "medication" and name and any(n and n in q for n in names):
            hits.append(ins)
        elif ins.kind in _KIND_WORDS and re.search(_KIND_WORDS[ins.kind], q):
            hits.append(ins)
    if not hits and re.search(r"drop|medic|pill|tablet|gota|pastilla|tableta", q):
        hits = [i for i in plan.instructions if i.kind == "medication"]
    if not hits:
        msg = ("Eso no está en sus documentos. Pregunte a su equipo de atención o farmacéutico."
               if lang == "es" else
               "That is not in your documents. Please ask your care team or pharmacist.")
        return AskResponse(answer=msg, citations=[], in_documents=False, urgent=False, mode=_mode())
    lead = "Sus documentos dicen (en inglés):" if lang == "es" else "Your documents say:"
    lines = [lead] + [f"• “{i.evidence.quote}”" for i in hits]
    if any(conflicts_for(i.id, plan.conflicts) for i in hits):
        lines.append(explain.T[lang]["conflict"])
    return AskResponse(answer="\n".join(lines),
                       citations=[Citation(**i.evidence.model_dump()) for i in hits],
                       in_documents=True, urgent=False, mode=_mode())


# ---------------------------------------------------------------- teach-back / barrier


@api.post("/teachback", response_model=TeachbackResponse)
def teachback_route(req: TeachbackRequest):
    plan = _case_or_404(req.case_id)
    ins = _instruction_or_404(plan, req.instruction_id)
    profile = store.get_or_create_profile(req.profile_id)
    if is_urgent(req.response_text):  # rule 5: urgent symptoms stop the normal flow
        return TeachbackResponse(labels=[], confidence=1.0,
                                 slot_check={"dose": "not_mentioned", "frequency": "not_mentioned",
                                             "duration": "not_mentioned"},
                                 source_conflict=False, feedback_text=urgent_message(profile.language),
                                 pathway="rules", mode=_mode())
    result = teachback.check(plan, ins, req.response_text, profile.language)
    profile.teach_back_history.append({"instruction_id": ins.id, "response_text": req.response_text,
                                       "labels": result["labels"]})
    style = learning.last_style(profile.profile_id)
    if style and not result["source_conflict"]:
        if "understood" in result["labels"]:
            learning.update_bandit(profile, style, 1.0, 1.0)
        elif any(l.endswith("_error") or l == "stop_negation" for l in result["labels"]):
            learning.update_bandit(profile, style, 0.0, 1.0)
    store.save_profile(profile)
    return TeachbackResponse(**result, mode=_mode())


@api.post("/barrier", response_model=BarrierResponse)
def barrier_route(req: BarrierRequest):
    _case_or_404(req.case_id)
    profile = store.get_or_create_profile(req.profile_id)
    result = barrier.respond(req.text, profile.language)
    example_id = store.save_example({"text": req.text, "predicted": result["labels"],
                                     "profile_id": profile.profile_id, "case_id": req.case_id})
    if not result["urgent"]:
        profile.concerns.append(Concern(id=example_id, text=req.text, labels=result["labels"]))
        store.save_profile(profile)
    return BarrierResponse(**result, example_id=example_id, mode=_mode())


# ---------------------------------------------------------------- feedback (self-learning)


@api.post("/feedback", response_model=FeedbackResponse)
def feedback(req: FeedbackRequest):
    profile = store.get_or_create_profile(req.profile_id)
    p = req.payload
    model_updated = False
    if req.kind == "thumbs":
        style = p.get("style") or learning.last_style(profile.profile_id) or profile.detail
        learning.update_bandit(profile, style, 1.0 if p.get("up", True) else 0.0, 0.3)
    elif req.kind == "term_tap":
        if not p.get("term"):
            raise HTTPException(422, "term_tap needs payload.term")
        learning.mark_term_confusing(profile, p["term"])
    elif req.kind == "style_change":
        style = p.get("style")
        if style not in profile.style_bandit:
            raise HTTPException(422, "style_change needs payload.style")
        learning.update_bandit(profile, style, 1.0, 2.0)  # explicit choice outweighs inferred signals
        if style in ("brief", "detailed"):
            profile.detail = style
    elif req.kind in ("label_confirm", "label_correct"):
        ex = store.get_example(p.get("example_id", ""))
        if not ex:
            raise HTTPException(404, "Unknown example_id")
        labels = ex["predicted"] if req.kind == "label_confirm" else list(p.get("labels", []))
        store.add_labeled({"text": ex["text"], "labels": labels, "source": req.kind})
        for c in profile.concerns:
            if c.id == ex["id"]:
                c.labels, c.confirmed = labels, True
        # Phase 3: learning.py calls SGDClassifier.partial_fit here and sets model_updated=True.
        model_updated = False
    store.save_profile(profile)
    return FeedbackResponse(profile=profile, model_updated=model_updated, mode=_mode())


# ---------------------------------------------------------------- briefing


@api.post("/briefing", response_model=BriefingResponse)
def briefing_route(req: BriefingRequest):
    plan = _case_or_404(req.case_id)
    profile = store.get_or_create_profile(req.profile_id)
    en, local, citations = briefing.build(plan, profile, req.include.concerns, req.include.conflicts)
    return BriefingResponse(draft_en=en, draft_patient_language=local, citations=citations, mode=_mode())


# ---------------------------------------------------------------- voice


@api.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form("en")):
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        raise HTTPException(503, "Voice input is not configured. Please type your answer instead.")
    audio = await file.read()
    lang = "es" if language.startswith("es") else "en"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.deepgram.com/v1/listen",
                params={"model": os.getenv("DEEPGRAM_MODEL", "nova-3"), "language": lang,
                        "smart_format": "true"},
                headers={"Authorization": f"Token {key}",
                         "Content-Type": file.content_type or "application/octet-stream"},
                content=audio,
            )
        r.raise_for_status()
        text = r.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception:
        raise HTTPException(502, "Voice transcription failed. Please type your answer instead.")
    return {"text": text, "language": lang, "mode": "live"}


# ---------------------------------------------------------------- eval / reset


def _read_artifact(name: str):
    path = store.ARTIFACTS_DIR / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@api.get("/eval")
def eval_results():
    ev, sim = _read_artifact("eval_results.json"), _read_artifact("bandit_sim.json")
    return {"available": ev is not None or sim is not None, "eval_results": ev, "bandit_sim": sim,
            "mode": _mode()}


@api.post("/demo/reset")
def demo_reset():
    store.reset()
    learning.reset()
    return {"ok": True, "mode": _mode()}


app.include_router(api)


@app.get("/")
def root():
    return {"service": "REXO API", "docs": "/docs", "health": "/api/health"}
