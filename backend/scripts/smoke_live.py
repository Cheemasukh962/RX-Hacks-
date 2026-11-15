"""End-to-end smoke test of the main REXO features over real HTTP.

Usage (from backend/):
    uvicorn app.main:app --port 8000          # in another terminal
    python scripts/smoke_live.py              # default http://localhost:8000
    python scripts/smoke_live.py https://rexo-api.onrender.com   # after deploy

Uses whatever keys the server has. Live-only checks (extraction, personalized
wording, voice) are reported as SKIP when the server is in demo mode.
Exit code 1 if any check FAILS.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # only used to synthesize test audio locally

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api"
FIX = Path(__file__).resolve().parent.parent / "fixtures"
c = httpx.Client(base_url=BASE, timeout=120)
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append(("PASS" if ok else "FAIL", name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""), flush=True)
    return ok


def skip(name: str, why: str) -> None:
    results.append(("SKIP", name, why))
    print(f"[SKIP] {name} — {why}", flush=True)


def post(path: str, **json):
    r = c.post(path, json=json)
    r.raise_for_status()
    return r.json()


def grounded(plan: dict) -> bool:
    docs = {d["id"]: d["text"] for d in plan["documents"]}
    return all(i["evidence"]["quote"] in docs.get(i["evidence"]["document_id"], "") for i in plan["instructions"])


def main() -> int:
    health = c.get("/health").json()
    live_llm = bool(health.get("llm"))
    print(f"server: {BASE}  health: {health}\n")

    c.post("/demo/reset")
    cases = c.get("/demo-cases").json()
    check("demo cases listed", len(cases) == 3, ", ".join(x["case_id"] for x in cases))

    # 1. Seeded cases + reconcile
    want = {"demo-cornea-001": 1, "demo-medication-002": 2, "demo-matching-003": 0}
    plans = {}
    for cid, n in want.items():
        plan = post("/cases", demo_case_id=cid)
        plans[cid] = plan
        types = [x["type"] for x in plan["conflicts"]]
        check(f"seeded {cid}: {n} conflict(s)", len(types) == n and grounded(plan), str(types))
    eye, med = plans["demo-cornea-001"], plans["demo-medication-002"]

    # 2. Pasted text → live extraction
    if live_llm:
        docs = [{"text": (FIX / "medication_avs.txt").read_text(encoding="utf-8")},
                {"text": (FIX / "medication_note.txt").read_text(encoding="utf-8")}]
        t = time.time()
        plan = post("/cases", documents=docs)
        types = sorted(x["type"] for x in plan["conflicts"])
        check("paste medication pair → live extraction", plan["mode"] == "live"
              and types == ["action_mismatch", "dose_mismatch"] and grounded(plan),
              f"{types}, {len(plan['instructions'])} instructions, {time.time() - t:.1f}s")
        avs = ("SYNTHETIC DEMO RECORD\nAFTER VISIT SUMMARY\nTake amoxicillin 500 mg by mouth three times "
               "daily for 10 days.\nFollow up in 2 weeks.")
        note = ("SYNTHETIC DEMO RECORD\nCLINICAL NOTE\nPlan: amoxicillin 500 mg PO TID x 7 days. "
                "Return in 2 weeks.")
        plan = post("/cases", documents=[{"text": avs}, {"text": note}])
        types = [x["type"] for x in plan["conflicts"]]
        check("paste unseen pair changes the result", "duration_mismatch" in types and grounded(plan), str(types))
    else:
        skip("live extraction", "server has no OPENAI_API_KEY (demo mode)")

    # 3. Profile + explain (EN + ES, every style)
    post("/profile", profile_id="smoke-en", language="en", detail="brief", modes=["read", "listen", "visual"],
         context_opt_in="I drive a delivery truck all day")
    post("/profile", profile_id="smoke-es", language="es", detail="detailed", modes=["read"])
    ins = next(i for i in eye["instructions"] if i["kind"] == "medication")
    for pid, style in [("smoke-en", "brief"), ("smoke-en", "analogy"), ("smoke-en", "detailed"),
                       ("smoke-es", None)]:
        body = {"case_id": eye["case_id"], "profile_id": pid, "instruction_id": ins["id"]}
        if style:
            body["style_override"] = style
        ex = post("/explain", **body)
        ok = ex["fact_check"]["passed"] and ex["citations"] and (ex["mode"] == "live" or not live_llm)
        check(f"explain {pid} {ex['style']} ({ex['mode']})", bool(ok), ex["text"][:110].replace("\n", " ") + "…")

    # 4. Ask
    a = post("/ask", case_id=med["case_id"], profile_id="smoke-en", question="How much lisinopril do I take?")
    check("ask: in documents, cited", a["in_documents"] and a["citations"], a["answer"][:100])
    a = post("/ask", case_id=med["case_id"], profile_id="smoke-en", question="Can I go scuba diving?")
    check("ask: not in documents → says so", not a["in_documents"], a["answer"][:100])

    # 5. Teach-back on the matching case (no conflicts)
    m = plans["demo-matching-003"]
    mi = next(i for i in m["instructions"] if i["kind"] == "medication" and i["frequency_per_day"])
    f = mi["frequency_per_day"]
    right = {1: "once a day", 2: "twice a day", 3: "three times a day", 4: "four times a day"}[f]
    wrong = "twice a day" if f != 2 else "once a day"
    tb = post("/teachback", case_id=m["case_id"], profile_id="smoke-en", instruction_id=mi["id"],
              response_text=f"I take {mi['dose'] or 'it'} {right}")
    check("teach-back correct answer", "understood" in tb["labels"], f"{tb['labels']} via {tb['pathway']}")
    tb = post("/teachback", case_id=m["case_id"], profile_id="smoke-en", instruction_id=mi["id"],
              response_text=f"I take it {wrong}")
    check("teach-back wrong frequency flagged", "frequency_error" in tb["labels"], f"{tb['labels']}")
    tb = post("/teachback", case_id=eye["case_id"], profile_id="smoke-es", instruction_id=ins["id"],
              response_text="Me pongo una gota dos veces al día")
    check("teach-back on conflicting instruction → source conflict", tb["source_conflict"],
          tb["feedback_text"][:100])

    # 6. Barrier → correction → classifier learns
    s = "Con el bebé no tengo ni un minuto para ponerme las gotas"
    b = post("/barrier", case_id=eye["case_id"], profile_id="smoke-es", text=s)
    fb = post("/feedback", profile_id="smoke-es", kind="label_correct",
              payload={"example_id": b["example_id"], "labels": ["schedule_conflict"]})
    b2 = post("/barrier", case_id=eye["case_id"], profile_id="smoke-es", text=s)
    check("barrier correction updates classifier", fb["model_updated"] and "schedule_conflict" in b2["labels"],
          f"before {b['labels']} → after {b2['labels']}")
    b = post("/barrier", case_id=eye["case_id"], profile_id="smoke-en", text="The drops cost too much")
    check("barrier: cost", "cost" in b["labels"], str(b["labels"]))

    # 7. Urgent
    b = post("/barrier", case_id=eye["case_id"], profile_id="smoke-en",
             text="My eye suddenly hurts a lot and I can't see")
    check("urgent symptoms → get help now", b["urgent"], b["support_text"][:90])

    # 8. Feedback / learning
    p0 = c.get("/profile/smoke-en").json()
    post("/feedback", profile_id="smoke-en", kind="term_tap", payload={"term": "ophthalmic"})
    p1 = post("/feedback", profile_id="smoke-en", kind="thumbs", payload={"style": "analogy", "up": True})["profile"]
    check("feedback updates profile", p1["style_bandit"]["analogy"] != p0["style_bandit"]["analogy"]
          and p1["term_scores"].get("ophthalmic", 1) < 0.5, f"analogy {p0['style_bandit']['analogy']}→"
          f"{p1['style_bandit']['analogy']}, ophthalmic {p1['term_scores'].get('ophthalmic')}")

    # 9. Briefing
    concerns = c.get("/profile/smoke-es").json()["concerns"]
    br = post("/briefing", case_id=eye["case_id"], profile_id="smoke-es",
              include={"concerns": [x["id"] for x in concerns[:1]], "conflicts": [eye["conflicts"][0]["id"]]})
    quotes_ok = all(q["quote"] in br["draft_en"] for q in br["citations"][:2])
    check("briefing: EN + ES drafts with quotes", bool(br["draft_en"] and br["draft_patient_language"]) and quotes_ok,
          f"{len(br['draft_en'])} / {len(br['draft_patient_language'])} chars")

    # 10. Voice (needs Deepgram on the server; audio generated with OpenAI TTS locally if a key is set)
    key = os.getenv("OPENAI_API_KEY")
    if key:
        try:
            r = httpx.post("https://api.openai.com/v1/audio/speech", timeout=60,
                           headers={"Authorization": f"Bearer {key}"},
                           json={"model": "gpt-4o-mini-tts", "voice": "alloy", "response_format": "mp3",
                                 "input": "I put in one drop four times a day."})
            r.raise_for_status()
            v = c.post("/voice/transcribe", files={"audio": ("a.mp3", r.content, "audio/mpeg")},
                       data={"language": "en"})
            if v.status_code == 503:
                skip("voice transcription", "server has no DEEPGRAM_API_KEY")
            else:
                text = v.json().get("text", "")
                check("voice transcription (Deepgram)", v.status_code == 200 and "drop" in text.lower(), text)
        except httpx.HTTPError as e:
            skip("voice transcription", f"could not generate test audio: {e}")
    else:
        skip("voice transcription", "no OPENAI_API_KEY locally to synthesize test audio")

    # 11. Eval + reset
    ev = c.get("/eval").json()
    check("eval artifacts available", ev["available"] and ev["eval_results"] is not None)
    check("demo reset", post("/demo/reset")["ok"])

    fails = [r for r in results if r[0] == "FAIL"]
    print(f"\n{sum(r[0] == 'PASS' for r in results)} passed, {len(fails)} failed, "
          f"{sum(r[0] == 'SKIP' for r in results)} skipped")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
