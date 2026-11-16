"""Camera medicine candidates, grounded in label fragments read by OpenAI vision or local OCR."""
import re

from . import store

KNOWN_LOCAL = {'meloxicam', 'mobic'}
# Brand -> generic, so a label read by brand matches documents that use the generic name.
GENERIC = {'mobic': 'meloxicam'}


def _name_pattern(names) -> re.Pattern:
    return re.compile(r'\b(' + '|'.join(re.escape(name) for name in sorted(names)) + r')\b', re.I)


def _matching_instructions(plan, names):
    if not plan or not names:
        return []
    pattern = _name_pattern(names)
    return [item for item in plan.instructions if item.medication_name and pattern.search(item.medication_name)]


def identify_result(scan: dict, case_id=None, language='en') -> dict:
    es = language == 'es'
    read = [field['value'].strip() for field in scan['fields'] if field['field'] in ('medication_name', 'brand')]
    names = {value.casefold() for value in read}
    if scan.get('engine') == 'openai-vision':
        # The vision model reads any medicine name; the patient still confirms before anything is said.
        medication = next((f['value'].strip() for f in scan['fields'] if f['field'] == 'medication_name'), None)
        found = bool(medication)
        display = medication.lower() if medication else None
    else:
        # Local OCR can garble text, so only the exact known label keywords count as a reading.
        found = bool(names & KNOWN_LOCAL)
        display = 'meloxicam' if found else None
    names |= {GENERIC[n] for n in names if n in GENERIC}
    strengths = sorted({field['value'].lower() for field in scan['fields'] if field['field'] == 'strength'})
    strength_fields = [field for field in scan['fields'] if field['field'] == 'strength']
    ranked = sorted(strength_fields, key=lambda field: field.get('supporting_passes', 1), reverse=True)
    # A sole candidate or uniquely dominant repeated reading can be offered for confirmation.
    strength = strengths[0] if len(strengths) == 1 else None
    if len(ranked) > 1 and ranked[0].get('supporting_passes', 1) >= 2 and ranked[0].get('supporting_passes', 1) > ranked[1].get('supporting_passes', 1):
        strength = ranked[0]['value'].lower()
    plan = store.get_case(case_id) if case_id else None
    matches = _matching_instructions(plan, names) if found else []
    citations = [item.evidence.model_dump() for item in matches]
    def normalized(value):
        return re.sub(r'\s+', '', value.lower()) if value else None
    # In this schema a tablet strength can be recorded as either strength or dose.
    documented = {value for item in matches for value in (item.strength, item.dose) if value and re.fullmatch(r'\d+(?:\.\d+)?\s*mg', value, re.I)}
    mismatch = bool(strength and documented and normalized(strength) not in {normalized(value) for value in documented})
    uncertain = bool(scan['conflicting_fields'])
    seen = f"{display}{(' ' + strength) if strength else ''}"
    prompt = (f"Leo {seen} en la etiqueta. ¿Es correcto?" if es else f"I read {seen} on the label. Is that right?") if found else ('No pude leer el nombre del medicamento. Acerque la etiqueta y evite reflejos.' if es else 'I could not read a medicine name. Move closer to the printed label and avoid glare.')
    confidences = [field['ocr_confidence'] for field in scan['fields'] if field['field'] == 'medication_name' and field.get('ocr_confidence') is not None]
    return {**scan, 'found': found, 'medication_name': display, 'strength_seen': strength, 'strength_candidates': strengths, 'matched_instruction_id': matches[0].id if matches else None, 'matched_instruction_ids': [item.id for item in matches], 'confidence': min(confidences or [0]), 'confidence_kind': 'uncalibrated_ocr_score_not_identity_probability', 'text_seen': scan['text'].splitlines(), 'confirm_prompt': prompt, 'strength_mismatch': mismatch, 'documented_strengths': sorted(documented), 'citations': citations, 'sources': [], 'requires_review': True, 'uncertain': uncertain}


def confirmed_intro(case_id=None, language='en', medication_name='meloxicam') -> dict:
    """Only document quotes. Draft general facts are intentionally not spoken."""
    es = language == 'es'
    name = medication_name.strip().lower()
    names = {name} | ({GENERIC[name]} if name in GENERIC else set())
    plan = store.get_case(case_id) if case_id else None
    matches = _matching_instructions(plan, names)
    citations = [item.evidence.model_dump() for item in matches]
    intro = f'Confirmaste la lectura de {name} en la etiqueta. ' if es else f'You confirmed the {name} label reading. '
    if matches:
        intro += ('Tus documentos dicen (citas originales): ' if es else 'Your documents say: ') + ' '.join(f'“{item.evidence.quote}”' for item in matches)
        if any(not c.resolved and any(item.id in c.instruction_ids for item in matches) for c in plan.conflicts):
            intro += ' Los documentos no coinciden. Tu equipo médico debe aclarar las instrucciones.' if es else ' The documents disagree. Your care team needs to clarify the instructions.'
    else:
        intro += 'Este medicamento no aparece en los documentos cargados. Consulta a tu farmacéutico.' if es else 'This medicine is not in the loaded documents. Ask your pharmacist about it.'
    return {'mode': 'demo', 'spoken_text': intro, 'citations': citations, 'sources': [], 'general_information_available': False, 'notice': 'The prepared drug fact sheet is DRAFT and needs human review before general-information narration is enabled.'}
