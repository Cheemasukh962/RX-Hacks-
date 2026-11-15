"""Build the synthetic teach-back + barrier training set (PLAN.md 8.1).

Deterministic template generation (seeded), English + Spanish. Labels are correct by
construction: each patient answer is generated from a known instruction with a known
perturbation (wrong dose, wrong frequency, stopping early, ...).

The hand-written held-out set (ml/data/heldout.csv) is written by the team and is NEVER
read by this script.

Run from backend/:  python -m ml.build_dataset
Writes: ml/data/train.jsonl, ml/data/synthetic_test.jsonl
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 1115
DATA_DIR = Path(__file__).resolve().parent / "data"
SOURCE = "synthetic-template-v1"

# ---------------------------------------------------------------- instruction pool (fictional)

MEDS = [
    # name, strength, unit, route, possible freqs, possible durations, dose counts
    ("prednisolone acetate ophthalmic suspension", "1%", "drop", "ophthalmic", [2, 4], [None], [1]),
    ("moxifloxacin ophthalmic solution", "0.5%", "drop", "ophthalmic", [3, 4], ["7 days", "1 week"], [1]),
    ("timolol ophthalmic solution", "0.5%", "drop", "ophthalmic", [1, 2], [None], [1]),
    ("artificial tears", None, "drop", "ophthalmic", [4], [None], [1, 2]),
    ("lisinopril", "10 mg", "tablet", "oral", [1], [None], [1]),
    ("metformin", "500 mg", "tablet", "oral", [1, 2], [None], [1, 2]),
    ("amoxicillin", "500 mg", "capsule", "oral", [2, 3], ["10 days", "7 days"], [1]),
    ("cephalexin", "500 mg", "capsule", "oral", [4], ["7 days"], [1]),
    ("prednisone", "20 mg", "tablet", "oral", [1], ["5 days"], [1, 2]),
    ("atorvastatin", "40 mg", "tablet", "oral", [1], [None], [1]),
    ("amlodipine", "5 mg", "tablet", "oral", [1], [None], [1]),
    ("ibuprofen", "400 mg", "tablet", "oral", [3], ["5 days"], [1]),
    ("losartan", "50 mg", "tablet", "oral", [1], [None], [1]),
]
DUES = ["1 week", "2 weeks", "4 weeks", "3 months", "10 days"]
DUE_DAYS = {"1 week": 7, "2 weeks": 14, "4 weeks": 28, "3 months": 90, "10 days": 10,
            "7 days": 7, "5 days": 5}

NUM_EN = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 7: "seven", 10: "ten", 14: "fourteen"}
NUM_ES = {1: "una", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 7: "siete", 10: "diez", 14: "catorce"}
UNIT = {
    "en": {"drop": ("drop", "drops"), "tablet": ("tablet", "tablets"), "capsule": ("capsule", "capsules"),
           "pill": ("pill", "pills")},
    "es": {"drop": ("gota", "gotas"), "tablet": ("tableta", "tabletas"), "capsule": ("cápsula", "cápsulas"),
           "pill": ("pastilla", "pastillas")},
}
FREQ = {
    "en": {1: ["once a day", "once daily", "one time a day", "every morning", "every day"],
           2: ["twice a day", "two times a day", "in the morning and at night", "every 12 hours", "2 times daily"],
           3: ["three times a day", "3 times a day", "every 8 hours", "with each meal"],
           4: ["four times a day", "4 times a day", "every 6 hours", "four times daily"]},
    "es": {1: ["una vez al día", "una vez por día", "cada mañana", "todos los días", "diario"],
           2: ["dos veces al día", "en la mañana y en la noche", "cada 12 horas", "2 veces al día"],
           3: ["tres veces al día", "3 veces al día", "cada 8 horas", "con cada comida"],
           4: ["cuatro veces al día", "4 veces al día", "cada 6 horas", "cuatro veces diarias"]},
}
DAYS_PHRASE = {
    "en": {5: ["5 days", "five days"], 7: ["7 days", "a week", "one week"], 10: ["10 days", "ten days"],
           14: ["2 weeks", "two weeks", "14 days"], 28: ["4 weeks", "four weeks"], 3: ["3 days", "three days"],
           90: ["3 months", "three months"], 30: ["a month", "one month"], 21: ["3 weeks", "three weeks"]},
    "es": {5: ["5 días", "cinco días"], 7: ["7 días", "una semana"], 10: ["10 días", "diez días"],
           14: ["2 semanas", "dos semanas"], 28: ["4 semanas", "cuatro semanas"], 3: ["3 días", "tres días"],
           90: ["3 meses", "tres meses"], 30: ["un mes", "1 mes"], 21: ["3 semanas", "tres semanas"]},
}
OPENERS = {
    "en": {"drop": ["I put", "I use", "I'm supposed to put", "I need to use", "So I put", "I'll use"],
           "pill": ["I take", "I'm supposed to take", "I need to take", "I'll take", "So I take", "I should take"]},
    "es": {"drop": ["Me pongo", "Uso", "Tengo que ponerme", "Debo usar", "Me voy a poner"],
           "pill": ["Tomo", "Tengo que tomar", "Debo tomar", "Me tomo", "Voy a tomar"]},
}
WHERE = {"en": " in my eye", "es": " en el ojo"}
FOR = {"en": "for", "es": "por"}
STOP_PHRASES = {
    "en": ["until it feels better", "and stop when I feel better", "until my eye stops hurting",
           "until the pain goes away", "but I'll stop once it looks better", "only until I feel okay"],
    "es": ["hasta que me sienta mejor", "y las dejo cuando me sienta mejor", "hasta que ya no me duela",
           "hasta que mi ojo se vea mejor", "pero lo dejo cuando ya esté bien"],
}
HEDGES = {
    "en": ["I'm not sure,", "I don't remember exactly, maybe", "Maybe", "No idea, maybe",
           "I can't remember, is it", "Not sure but"],
    "es": ["No estoy seguro,", "No me acuerdo bien, tal vez", "Tal vez", "No sé, quizás",
           "No estoy segura, ¿será"],
}
PURE_UNSURE = {
    "en": ["I don't know", "I'm not sure how much to use", "I can't remember what they told me",
           "Honestly I have no idea", "I forgot what the paper said"],
    "es": ["No sé", "No me acuerdo de lo que me dijeron", "No estoy segura de cuánto usar",
           "La verdad no tengo idea", "Se me olvidó lo que decía el papel"],
}
FOLLOWUP = {
    "en": ["I come back in {x}", "My next appointment is in {x}", "I need to see the doctor again in {x}",
           "Follow up in {x}", "I go back to the clinic in {x}"],
    "es": ["Regreso en {x}", "Mi próxima cita es en {x}", "Tengo que volver con el doctor en {x}",
           "Vuelvo a la clínica en {x}"],
}
LAB = {
    "en": ["I get my blood test in {x}", "The lab work is in {x}", "I need the blood draw in {x}"],
    "es": ["Me hago el análisis en {x}", "El examen de sangre es en {x}", "Tengo que hacerme la prueba en {x}"],
}


def _instr(rng: random.Random) -> dict:
    name, strength, unit, route, freqs, durs, counts = rng.choice(MEDS)
    n = rng.choice(counts)
    dose = f"{n} {unit}{'s' if n > 1 else ''}"
    return {"kind": "medication", "medication_name": name, "strength": strength, "dose": dose,
            "route": route, "frequency_per_day": rng.choice(freqs), "duration": rng.choice(durs),
            "action": rng.choice(["start", "continue", None]), "due": None,
            "_unit": unit, "_count": n}


def _dose_phrase(n: int, unit: str, lang: str, rng: random.Random) -> str:
    if unit == "tablet" and rng.random() < 0.3:
        unit = "pill"
    word = UNIT[lang][unit][0 if n == 1 else 1]
    num = str(n) if rng.random() < 0.4 else (NUM_ES if lang == "es" else NUM_EN).get(n, str(n))
    return f"{num} {word}"


def _days_phrase(days: int, lang: str, rng: random.Random) -> str:
    return rng.choice(DAYS_PHRASE[lang][days])


def _wrong(value, options, rng):
    return rng.choice([o for o in options if o != value])


def _teachback_sentence(ins: dict, lang: str, rng: random.Random, *, dose_n=None, freq=None,
                        days=None, mention_dose=True, mention_dur=False, stop=False, hedge=False) -> str:
    unit = ins["_unit"]
    kind = "drop" if unit == "drop" else "pill"
    opener = rng.choice(OPENERS[lang][kind])
    dose_txt = _dose_phrase(dose_n, unit, lang, rng) if mention_dose else ("it" if lang == "en" else "")
    if lang == "es" and not mention_dose:
        opener = {"Me pongo": "Me las pongo", "Uso": "Las uso", "Tengo que ponerme": "Tengo que ponérmelas",
                  "Debo usar": "Debo usarlas", "Me voy a poner": "Me las voy a poner", "Tomo": "La tomo",
                  "Tengo que tomar": "Tengo que tomarla", "Debo tomar": "Debo tomarla", "Me tomo": "Me la tomo",
                  "Voy a tomar": "Voy a tomarla"}[opener]
    where = WHERE[lang] if unit == "drop" and rng.random() < 0.6 else ""
    parts = [opener, dose_txt + where if dose_txt else where.strip(), rng.choice(FREQ[lang][freq])]
    if mention_dur and days:
        parts.append(f"{FOR[lang]} {_days_phrase(days, lang, rng)}")
    if stop:
        parts.append(rng.choice(STOP_PHRASES[lang]))
    s = " ".join(p for p in parts if p).strip()
    if rng.random() < 0.25:  # frequency-first word order (must keep every slot the label depends on)
        s = f"{rng.choice(FREQ[lang][freq]).capitalize()}, {dose_txt or ''}".strip().rstrip(",")
        if dose_txt == "" or dose_txt == "it":
            s = rng.choice(FREQ[lang][freq]).capitalize()
        if mention_dur and days:
            s += f" {FOR[lang]} {_days_phrase(days, lang, rng)}"
        if stop:
            s += " " + rng.choice(STOP_PHRASES[lang])
    if hedge:
        h = rng.choice(HEDGES[lang])
        s = f"{h} {s[0].lower() + s[1:]}"
        if h.endswith("¿será"):
            s += "?"
    return s + ("" if s.endswith("?") else rng.choice([".", "", "."]))


def teachback_examples(rng: random.Random, per_lang: int) -> list[dict]:
    out = []
    for lang in ("en", "es"):
        for _ in range(per_lang):
            r = rng.random()
            if r < 0.15:  # follow-up / lab timing
                kind = rng.choice(["follow_up", "lab"])
                due = rng.choice(DUES)
                ins = {"kind": kind, "due": due}
                days = DUE_DAYS[due]
                bank = FOLLOWUP if kind == "follow_up" else LAB
                if rng.random() < 0.55:
                    said, labels = days, ["understood"]
                else:
                    said = _wrong(days, [7, 14, 21, 28, 90, 10, 3], rng)
                    labels = ["followup_timing_error"]
                text = rng.choice(bank[lang]).format(x=_days_phrase(said, lang, rng))
                if rng.random() < 0.15:
                    text = f"{rng.choice(HEDGES[lang])} {text[0].lower() + text[1:]}"
                    labels = [l for l in labels if l != "understood"] + ["uncertain"]
                out.append({"lang": lang, "instruction": ins, "text": text, "labels": labels})
                continue

            ins = _instr(rng)
            n, f = ins["_count"], ins["frequency_per_day"]
            dur_days = DUE_DAYS.get(ins["duration"]) if ins["duration"] else None
            kw = dict(dose_n=n, freq=f, days=dur_days, mention_dose=rng.random() < 0.75,
                      mention_dur=bool(dur_days) and rng.random() < 0.5)
            labels: list[str] = []
            case = rng.random()
            if case < 0.08:  # pure uncertainty, no content
                out.append({"lang": lang, "instruction": ins, "text": rng.choice(PURE_UNSURE[lang]),
                            "labels": ["uncertain"]})
                continue
            if 0.30 <= case < 0.45:
                kw["dose_n"] = _wrong(n, [1, 2, 3], rng)
                kw["mention_dose"] = True
                labels.append("dose_error")
            elif 0.45 <= case < 0.60:
                kw["freq"] = _wrong(f, [1, 2, 3, 4], rng)
                labels.append("frequency_error")
            elif 0.60 <= case < 0.72 and dur_days:
                kw["days"] = _wrong(dur_days, [3, 5, 7, 10, 14, 30], rng)
                kw["mention_dur"] = True
                labels.append("duration_error")
            elif 0.72 <= case < 0.78:
                kw["dose_n"] = _wrong(n, [1, 2, 3], rng)
                kw["freq"] = _wrong(f, [1, 2, 3, 4], rng)
                kw["mention_dose"] = True
                labels += ["dose_error", "frequency_error"]
            if 0.78 <= case < 0.90:
                kw["stop"] = True
                labels.append("stop_negation")
            if rng.random() < 0.12:
                kw["hedge"] = True
                labels.append("uncertain")
            if not labels:
                labels = ["understood"]
            text = _teachback_sentence(ins, lang, rng, **kw)
            out.append({"lang": lang, "instruction": ins, "text": text, "labels": labels})
    for ex in out:
        ex["instruction"] = {k: v for k, v in ex["instruction"].items() if not k.startswith("_")}
        ex["task"] = "teachback"
    return out


# ---------------------------------------------------------------- barrier

MED_REF = {"en": ["the drops", "these drops", "my eye drops", "the pills", "my medicine", "these tablets",
                  "the medication"],
           "es": ["las gotas", "estas gotas", "las pastillas", "mi medicina", "el medicamento", "estas tabletas"]}
BARRIER = {
    "side_effect": {
        "en": ["{med} make my eye feel gritty", "{med} burn when I put them in", "{med} make me dizzy",
               "I get headaches from {med}", "{med} upset my stomach", "my vision gets blurry after {med}",
               "I've had a rash since starting {med}", "{med} sting a lot", "I feel sick after taking {med}",
               "{med} give me a dry cough", "my eye feels scratchy after {med}"],
        "es": ["{med} me hacen sentir el ojo arenoso", "{med} me arden cuando me las pongo", "{med} me marean",
               "me da dolor de cabeza con {med}", "{med} me caen mal al estómago",
               "veo borroso después de {med}", "me salió un sarpullido desde que empecé {med}",
               "{med} me pican mucho", "me siento mal después de tomar {med}", "{med} me dan tos seca"]},
    "cost": {
        "en": ["I can't afford {med}", "{med} are too expensive", "my insurance won't cover {med}",
               "the copay is too high", "I don't have the money for {med} this month"],
        "es": ["no puedo pagar {med}", "{med} están muy caras", "mi seguro no cubre {med}",
               "el copago es muy alto", "no tengo dinero para {med} este mes"]},
    "ran_out_refill": {
        "en": ["I ran out of {med}", "I'm almost out of {med}", "the pharmacy said I have no refills left",
               "I used up the bottle already", "I haven't been able to pick up the refill"],
        "es": ["se me acabaron {med}", "ya casi no me quedan {med}", "la farmacia dice que no tengo más resurtidos",
               "ya se terminó el frasco", "no he podido recoger la receta"]},
    "forgot": {
        "en": ["I keep forgetting {med}", "I forget the afternoon dose", "I missed a few days because I forgot",
               "I never remember the night dose", "it just slips my mind"],
        "es": ["se me olvidan {med}", "se me olvida la dosis de la tarde", "no me acuerdo de la dosis de la noche",
               "falté unos días porque se me olvidó", "simplemente se me pasa"]},
    "schedule_conflict": {
        "en": ["I work night shifts so the schedule doesn't fit", "I can't use {med} at work",
               "four times a day doesn't work with my job", "I'm driving all day for work",
               "my shifts change every week"],
        "es": ["trabajo de noche y el horario no me funciona", "no puedo usar {med} en el trabajo",
               "cuatro veces al día no me funciona con mi trabajo", "mis turnos cambian cada semana",
               "manejo todo el día por mi trabajo"]},
    "doesnt_see_importance": {
        "en": ["I feel fine so I don't think I need {med}", "{med} don't seem to do anything",
               "my eye looks okay now, why keep going", "I don't see the point of {med}",
               "I don't think {med} are helping"],
        "es": ["me siento bien, no creo que necesite {med}", "{med} no hacen nada",
               "mi ojo ya se ve bien, ¿para qué seguir?", "no le veo el sentido a {med}",
               "no creo que {med} me ayuden"]},
    "confusion": {
        "en": ["I don't understand which drops to use when", "the two papers say different things and I'm confused",
               "I'm not sure how to use {med}", "I can't tell which bottle is which", "the instructions are confusing"],
        "es": ["no entiendo cuáles gotas usar y cuándo", "los dos papeles dicen cosas distintas y estoy confundido",
               "no sé cómo usar {med}", "no distingo cuál frasco es cuál", "las instrucciones son confusas"]},
}
STOP_SUFFIX = {"en": ["I'm thinking of stopping.", "I want to quit {med}.", "I'm ready to give up on {med}.",
                      "I already stopped using them.", "I don't want to keep going."],
               "es": ["Estoy pensando en dejarlas.", "Quiero dejar {med}.", "Ya no quiero usar {med}.",
                      "Voy a suspender {med}.", "Ya las dejé de usar."]}
STOP_ALONE = {"en": ["I want to stop {med}", "I'm going to quit taking {med}", "I'm done with {med}"],
              "es": ["Quiero dejar {med}", "Voy a dejar de tomar {med}", "Ya no voy a usar {med}"]}
NO_BARRIER = {"en": ["When is my next appointment?", "Can I take {med} with food?", "What does inflammation mean?",
                     "My daughter will drive me to the clinic", "Everything is going well with {med}"],
              "es": ["¿Cuándo es mi próxima cita?", "¿Puedo tomar {med} con comida?", "¿Qué significa inflamación?",
                     "Mi hija me lleva a la clínica", "Todo va bien con {med}"]}
COMBOS = [("cost", "ran_out_refill"), ("schedule_conflict", "forgot"), ("side_effect", "doesnt_see_importance")]


def _fill(t: str, lang: str, rng: random.Random) -> str:
    s = t.format(med=rng.choice(MED_REF[lang]))
    return s[0].upper() + s[1:]


def barrier_examples(rng: random.Random, per_lang: int) -> list[dict]:
    out = []
    labels_all = list(BARRIER)
    for lang in ("en", "es"):
        for _ in range(per_lang):
            r = rng.random()
            if r < 0.07:
                out.append({"lang": lang, "text": _fill(rng.choice(NO_BARRIER[lang]), lang, rng), "labels": []})
                continue
            if r < 0.14:
                out.append({"lang": lang, "text": _fill(rng.choice(STOP_ALONE[lang]), lang, rng) + ".",
                            "labels": ["wants_to_stop"]})
                continue
            if r < 0.24:
                a, b = rng.choice(COMBOS)
                text = (_fill(rng.choice(BARRIER[a][lang]), lang, rng) + (" and " if lang == "en" else " y ")
                        + rng.choice(BARRIER[b][lang]).format(med=rng.choice(MED_REF[lang])))
                labels = [a, b]
            else:
                a = rng.choice(labels_all)
                text = _fill(rng.choice(BARRIER[a][lang]), lang, rng)
                labels = [a]
            text += "."
            if rng.random() < 0.4:
                text += " " + _fill(rng.choice(STOP_SUFFIX[lang]), lang, rng)
                labels.append("wants_to_stop")
            out.append({"lang": lang, "text": text, "labels": labels})
    for ex in out:
        ex["task"] = "barrier"
        ex["instruction"] = None
    return out


def build(tb_per_lang: int = 300, br_per_lang: int = 220, test_frac: float = 0.2) -> dict:
    rng = random.Random(SEED)
    rows = teachback_examples(rng, tb_per_lang) + barrier_examples(rng, br_per_lang)
    # drop exact duplicates (same task + text + instruction) so train/test cannot share a sentence
    seen, uniq = set(), []
    for r in rows:
        key = (r["task"], r["text"].lower(), json.dumps(r["instruction"], sort_keys=True))
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    rng.shuffle(uniq)
    for i, r in enumerate(uniq):
        r["id"] = f"syn-{i:04d}"
        r["source"] = SOURCE
    # split by unique text so the same sentence never lands in both train and test
    texts = sorted({r["text"].lower() for r in uniq})
    rng.shuffle(texts)
    test_texts = set(texts[: int(len(texts) * test_frac)])
    train = [r for r in uniq if r["text"].lower() not in test_texts]
    test = [r for r in uniq if r["text"].lower() in test_texts]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in (("train.jsonl", train), ("synthetic_test.jsonl", test)):
        with (DATA_DIR / name).open("w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"train": len(train), "synthetic_test": len(test), "dropped_duplicates": len(rows) - len(uniq)}


if __name__ == "__main__":
    print(build())
