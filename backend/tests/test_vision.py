"""Synthetic-only OCR checks. No personal bottle photos are committed."""
import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from app.main import app
from app.vision import VisionError, decode_image, extract_label_fields, recognize_bottle


def synthetic_label(back=False, rotation=0):
    canvas = Image.new('RGB', (1300, 950), '#eee8dd')
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((100, 100, 1200, 850), radius=20, fill='#f1d45d')
    paths = ['/System/Library/Fonts/Supplemental/Arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for path in paths:
        try:
            font = ImageFont.truetype(path, 44)
            break
        except OSError:
            continue
    else:
        pytest.skip('A scalable test font is not installed')
    lines = ['SYNTHETIC DEMO LABEL', 'MELOXICAM 15 MG TABLET', 'Generic for: Mobic', 'Take 1 tablet by mouth daily.', 'Refills: 2'] if not back else ['SYNTHETIC DEMO LABEL', 'Take with food', 'Qty: 30 TAB', 'Discard After: 08Oct2027']
    for index, text in enumerate(lines):
        draw.text((145, 180 + index * 105), text, font=font, fill='black')
    if rotation:
        canvas = canvas.rotate(rotation, fillcolor='#eee8dd')
    output = io.BytesIO()
    canvas.save(output, 'PNG')
    return output.getvalue()


def test_parser_only_returns_supported_fragments():
    lines = [{'text': text, 'ocr_confidence': .91} for text in ['Fictional Person', 'Rx# 999 888 777', 'Name: Fictional Person', 'MELOXICAM 15 MG TABLET', 'Take 1 tablet by mouth daily. Fictional Person', 'Generic for: Mobic', 'Take with food', 'Qty: 30 TAB', 'Refills: 2']]
    fields, safe, _ = extract_label_fields(lines)
    values = {item['field']: item['value'] for item in fields}
    assert values['medication_name'] == 'MELOXICAM'
    assert values['strength'] == '15 MG'
    assert values['quantity'] == '30 TAB'
    assert values['refills'] == '2'
    assert 'Fictional Person' not in '\n'.join(safe)
    assert '999' not in '\n'.join(safe)
    assert all(item['evidence']['quote'] in '\n'.join(safe) for item in fields)


def test_disagreeing_candidates_are_retained():
    fields, _, _ = extract_label_fields([{'text': 'MELOXICAM 15 MG TABLET'}, {'text': 'MELOXICAM 75 MG TABLET'}])
    assert {item['value'] for item in fields if item['field'] == 'strength'} == {'15 MG', '75 MG'}
    assert all(item['status'] == 'needs_review' for item in fields)


def test_missing_values_are_not_invented():
    fields, safe, _ = extract_label_fields([{'text': 'Take with food'}])
    assert [item['field'] for item in fields] == ['food_instruction']
    assert safe == ['Take with food']


@pytest.mark.parametrize('image_format', ['JPEG', 'MPO', 'PNG', 'WEBP'])
def test_supported_photo_formats(image_format):
    output = io.BytesIO()
    image = Image.new('RGB', (240, 320), 'white')
    if image_format == 'MPO':
        image.save(output, format='MPO', save_all=True, append_images=[image.copy()])
        with Image.open(io.BytesIO(output.getvalue())) as stored:
            assert stored.format == 'MPO'
    else:
        image.save(output, format=image_format)
    decoded = decode_image(output.getvalue())
    assert decoded.shape == (320, 240, 3)


def test_unsupported_format_error_names_actual_format():
    output = io.BytesIO()
    Image.new('RGB', (240, 320), 'white').save(output, format='BMP')
    with pytest.raises(VisionError, match='Detected BMP image data'):
        decode_image(output.getvalue())


def test_invalid_image_and_size_rejected():
    for payload in [b'', b'not an image', b'x' * (8 * 1024 * 1024 + 1)]:
        with pytest.raises(VisionError):
            decode_image(payload)


@pytest.mark.skipif(not shutil.which('tesseract'), reason='System Tesseract is not installed')
@pytest.mark.parametrize('rotation', [0, 6])
def test_actual_ocr_synthetic_front(rotation):
    result = recognize_bottle(synthetic_label(rotation=rotation))
    values = {(item['field'], item['value'].upper()) for item in result['fields']}
    assert ('medication_name', 'MELOXICAM') in values
    assert ('strength', '15 MG') in values
    assert result['requires_review'] is True
    assert result['preview_png_b64']
    assert result['mode'] == 'live'


@pytest.mark.skipif(not shutil.which('tesseract'), reason='System Tesseract is not installed')
def test_actual_ocr_synthetic_back():
    result = recognize_bottle(synthetic_label(back=True))
    values = {item['field']: item['value'] for item in result['fields']}
    assert any(item['field'] == 'quantity' and item['value'].upper() == '30 TAB' for item in result['fields'])
    # Never overwrite a complete candidate when another OCR pass drops the unit.
    assert all(item['status'] == 'needs_review' for item in result['fields'])
    assert 'food_instruction' in values


def test_upload_endpoint_uses_local_pipeline(monkeypatch):
    monkeypatch.setattr('app.vision.recognize_bottle', lambda payload: {'mode': 'live', 'text': 'MELOXICAM 15 MG', 'requires_review': True})
    result = TestClient(app).post('/api/ingest/photo', files={'image': ('label.png', b'synthetic bytes', 'image/png')})
    assert result.status_code == 200
    assert result.json()['requires_review'] is True


def test_invalid_upload_returns_clear_error():
    result = TestClient(app).post('/api/ingest/photo', files={'image': ('bad.png', b'invalid', 'image/png')})
    assert result.status_code == 422
    assert 'decoded' in result.json()['detail']


def test_medicine_identification_does_not_guess_unknown_name():
    from app.medicine import identify_result
    scan = {'mode': 'live', 'fields': [{'field': 'medication_name', 'value': 'NOTMELOXICAM', 'ocr_confidence': .95}], 'text': 'NOTMELOXICAM', 'conflicting_fields': []}
    result = identify_result(scan)
    assert result['found'] is False
    assert result['matched_instruction_id'] is None


def test_medicine_identification_requires_exact_keyword_and_preserves_strength_uncertainty():
    from app.medicine import identify_result
    scan = {'mode': 'live', 'fields': [{'field': 'medication_name', 'value': 'MELOXICAM', 'ocr_confidence': .95}, {'field': 'strength', 'value': '15 MG'}, {'field': 'strength', 'value': '75 MG'}], 'text': 'MELOXICAM', 'conflicting_fields': ['strength']}
    result = identify_result(scan)
    assert result['found'] is True
    assert result['strength_seen'] is None
    assert len(result['strength_candidates']) == 2
    assert result['requires_review'] is True


def test_intro_requires_confirmation():
    result = TestClient(app).post('/api/medicine/intro', json={'medication_name': 'meloxicam'})
    assert result.status_code == 422


def test_confirmed_intro_without_case_does_not_invent_patient_instructions():
    result = TestClient(app).post('/api/medicine/intro', json={'medication_name': 'meloxicam', 'confirmed': True})
    assert result.status_code == 200
    assert result.json()['citations'] == []
    assert result.json()['general_information_available'] is False
    assert 'not in the loaded documents' in result.json()['spoken_text']


def test_blurry_blank_frame_rejected_before_ocr():
    output = io.BytesIO()
    Image.new('RGB', (400, 400), 'white').save(output, 'PNG')
    with pytest.raises(VisionError, match='blurry'):
        recognize_bottle(output.getvalue())


def test_camera_offers_dominant_repeated_strength_but_keeps_other_candidates():
    from app.medicine import identify_result
    scan = {'mode': 'live', 'fields': [{'field': 'medication_name', 'value': 'MELOXICAM', 'ocr_confidence': .95}, {'field': 'strength', 'value': '15 MG', 'supporting_passes': 4}, {'field': 'strength', 'value': '45 MG', 'supporting_passes': 1}], 'text': 'MELOXICAM', 'conflicting_fields': ['strength']}
    result = identify_result(scan)
    assert result['strength_seen'] == '15 mg'
    assert result['strength_candidates'] == ['15 mg', '45 mg']
    assert result['requires_review'] is True


def test_strength_mismatch_is_compared_to_document_evidence():
    from app import store
    from app.medicine import identify_result, confirmed_intro
    from app.schemas import CarePlan, Document, Instruction, Evidence
    quote = 'Take meloxicam 15 mg once daily.'
    plan = CarePlan(case_id='ocr-synthetic-strength-test', documents=[Document(id='avs-ocr', type='after_visit_summary', title='Synthetic label test', text=quote)], instructions=[Instruction(id='med-ocr', kind='medication', medication_name='meloxicam', dose='15 mg', evidence=Evidence(document_id='avs-ocr', quote=quote))])
    store.save_case(plan)
    scan = {'mode': 'live', 'fields': [{'field': 'medication_name', 'value': 'MELOXICAM', 'ocr_confidence': .9}, {'field': 'strength', 'value': '7.5 MG'}], 'text': 'MELOXICAM 7.5 MG', 'conflicting_fields': []}
    result = identify_result(scan, plan.case_id)
    assert result['strength_mismatch'] is True
    assert result['matched_instruction_id'] == 'med-ocr'
    assert result['citations'][0]['quote'] == quote
    intro = confirmed_intro(plan.case_id)
    assert quote in intro['spoken_text']
    assert intro['sources'] == []
