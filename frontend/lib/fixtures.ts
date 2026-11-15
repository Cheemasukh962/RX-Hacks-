import type { DemoCase, DocumentType } from './types';

export const demoCases: DemoCase[] = [
  { case_id: 'demo-cornea-001', title: 'After an eye procedure', description: 'Two documents. One question about your eye drops.', mode: 'demo' },
  { case_id: 'demo-medication-002', title: 'Managing blood pressure', description: 'Take a closer look at instructions that disagree.', mode: 'demo' },
  { case_id: 'demo-matching-003', title: 'A matching pair', description: 'Explore a care plan with consistent instructions.', mode: 'demo' },
];

export const fixtureTexts: Record<string, { text: string; type_hint: DocumentType }[]> = {
  'demo-cornea-001': [
    { type_hint: 'after_visit_summary', text: 'SYNTHETIC DEMO RECORD — NOT A REAL PATIENT\nAFTER-VISIT SUMMARY\nUse prednisolone acetate ophthalmic suspension 1%, one drop in the operated eye four times daily.\nFollow-up visit on November 25, 2026.\nCall your care team promptly for increasing eye pain or redness.' },
    { type_hint: 'clinical_note', text: 'SYNTHETIC DEMO RECORD — NOT A REAL PATIENT\nCLINICAL NOTE\nContinue prednisolone acetate ophthalmic suspension 1%, one drop in the operated eye twice daily.\nThe drops reduce inflammation and the risk of graft rejection.\nInflammation means swelling and irritation. Graft rejection means the body attacks the transplanted tissue.\nFollow-up visit on November 25, 2026.' },
  ],
  'demo-medication-002': [
    { type_hint: 'after_visit_summary', text: 'SYNTHETIC DEMO RECORD — NOT A REAL PATIENT\nAFTER-VISIT SUMMARY\nTake lisinopril 10 mg once daily.\nContinue ibuprofen as needed.\nFollow-up visit on December 1, 2026.' },
    { type_hint: 'clinical_note', text: 'SYNTHETIC DEMO RECORD — NOT A REAL PATIENT\nCLINICAL NOTE\nTake lisinopril 20 mg daily.\nAvoid NSAIDs, including ibuprofen.\nFollow-up visit on December 1, 2026.' },
  ],
  'demo-matching-003': [
    { type_hint: 'after_visit_summary', text: 'SYNTHETIC DEMO RECORD — NOT A REAL PATIENT\nAFTER-VISIT SUMMARY\nTake lisinopril 10 mg once daily.\nFollow-up visit on December 1, 2026.' },
    { type_hint: 'clinical_note', text: 'SYNTHETIC DEMO RECORD — NOT A REAL PATIENT\nCLINICAL NOTE\nTake lisinopril 10 mg once daily.\nFollow-up visit on December 1, 2026.' },
  ],
};
