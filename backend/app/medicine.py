"""Camera medicine candidates, grounded in locally read label fragments."""
import re

from . import store


def identify_result(scan: dict, case_id=None, language='en') -> dict:
    es = language == 'es'
    names = {field['value'].casefold().strip() for field in scan['fields'] if field['field'] in ('medication_name', 'brand')}
    found = bool(names & {'meloxicam', 'mobic'})
    strengths = sorted({field['value'].lower() for field in scan['fields'] if field['field'] == 'strength'})
    strength_fields = [field for field in scan['fields'] if field['field'] == 'strength']
    ranked = sorted(strength_fields, key=lambda field: field.get('supporting_passes', 1), reverse=True)
    # A sole candidate or uniquely dominant repeated reading can be offered for confirmation.
    strength = strengths[0] if len(strengths) == 1 else None
    if len(ranked) > 1 and ranked[0].get('supporting_passes', 1) >= 2 and ranked[0].get('supporting_passes', 1) > ranked[1].get('supporting_passes', 1):
        strength = ranked[0]['value'].lower()
    plan = store.get_case(case_id) if case_id else None
    matches = [item for item in plan.instructions if item.medication_name and re.search(r'\b(meloxicam|mobic)\b', item.medication_name, re.I)] if plan and found else []
    citations = [item.evidence.model_dump() for item in matches]
    def normalized(value):
        return re.sub(r'\s+', '', value.lower()) if value else None
    # In this schema a tablet strength can be recorded as either strength or dose.
    documented = {value for item in matches for value in (item.strength, item.dose) if value and re.fullmatch(r'\d+(?:\.\d+)?\s*mg', value, re.I)}
    mismatch = bool(strength and documented and normalized(strength) not in {normalized(value) for value in documented})
    uncertain = bool(scan['conflicting_fields'])
    prompt = (f"Leo meloxicam{(' ' + strength) if strength else ''} en la etiqueta. ¿Es correcto?" if es else f"I read meloxicam{(' ' + strength) if strength else ''} on the label. Is that right?") if found else ('No pude identificar una etiqueta de meloxicam. Acerca el texto o escríbelo.' if es else 'I could not identify a meloxicam label. Move closer to the printed text, or type it.')
    return {**scan, 'found': found, 'medication_name': 'meloxicam' if found else None, 'strength_seen': strength, 'strength_candidates': strengths, 'matched_instruction_id': matches[0].id if matches else None, 'matched_instruction_ids': [item.id for item in matches], 'confidence': min([field['ocr_confidence'] for field in scan['fields'] if field['field'] == 'medication_name'] or [0]), 'confidence_kind': 'uncalibrated_ocr_score_not_identity_probability', 'text_seen': scan['text'].splitlines(), 'confirm_prompt': prompt, 'strength_mismatch': mismatch, 'documented_strengths': sorted(documented), 'citations': citations, 'sources': [], 'requires_review': True, 'uncertain': uncertain}


def confirmed_intro(case_id=None, language='en') -> dict:
    """Only document quotes. Draft general facts are intentionally not spoken."""
    es = language == 'es'
    plan = store.get_case(case_id) if case_id else None
    matches = [item for item in plan.instructions if item.medication_name and re.search(r'\b(meloxicam|mobic)\b', item.medication_name, re.I)] if plan else []
    citations = [item.evidence.model_dump() for item in matches]
    intro = 'Confirmaste la lectura de meloxicam en la etiqueta. ' if es else 'You confirmed the meloxicam label reading. '
    if matches:
        intro += ('Tus documentos dicen (citas originales): ' if es else 'Your documents say: ') + ' '.join(f'“{item.evidence.quote}”' for item in matches)
        if any(not c.resolved and any(item.id in c.instruction_ids for item in matches) for c in plan.conflicts):
            intro += ' Los documentos no coinciden. Tu equipo médico debe aclarar las instrucciones.' if es else ' The documents disagree. Your care team needs to clarify the instructions.'
    else:
        intro += 'Este medicamento no aparece en los documentos cargados. Consulta a tu farmacéutico.' if es else 'This medicine is not in the loaded documents. Ask your pharmacist about it.'
    return {'mode': 'demo', 'spoken_text': intro, 'citations': citations, 'sources': [], 'general_information_available': False, 'notice': 'The prepared drug fact sheet is DRAFT and needs human review before general-information narration is enabled.'}
