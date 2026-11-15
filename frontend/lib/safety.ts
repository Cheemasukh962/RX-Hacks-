import type { CarePlan, Evidence, Instruction } from './types';

// Conservative demo guard, not a symptom assessment or a clinical triage system.
export function isUrgent(text: string): boolean {
  const folded = text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replaceAll('’', "'");
  return /chest (pain|pressure|tightness)|pain in my chest|(trouble|difficulty|hard) breathing|can(?:not|'t) breathe|short(ness)? of breath|(sudden(ly)?|all of a sudden).{0,20}(vision|see|blind)|(lost|losing) (my )?(vision|sight)|can't see|went blind|face (is )?droop|slurred speech|stroke|(numb|weak)(ness)? on one side|suicid|kill myself|end my life|hurt myself|self[- ]harm|want to die|dolor (de|en el) pecho|presion en el pecho|no puedo respirar|(dificultad|problemas?) para respirar|me falta el aire|perdi (la )?(vista|vision)|perdida (repentina )?de (la )?vision|no puedo ver|me quede ciego|derrame|cara caida|no puedo hablar|(entumecid|debil).{0,20}un lado|matarme|quitarme la vida|hacerme dano|quiero morir|call 911|llam[ae] al 911/.test(folded);
}

export function redactText(text: string) {
  let count = 0;
  const redacted = text.replace(/^\s*(?:patient(?: name)?|name|dob|date of birth|mrn|medical record(?: number)?|address|phone|email)\s*[:=].*$/gim, () => { count++; return '[Identifier removed]'; });
  return { text: redacted, count };
}

export function verifiedEvidence(plan: CarePlan, evidence: Evidence) {
  return !!evidence.quote && plan.documents.some(doc => doc.id === evidence.document_id && doc.text.includes(evidence.quote));
}

export function hasConflict(plan: CarePlan, instruction: Instruction) {
  return plan.conflicts.some(conflict => !conflict.resolved && conflict.instruction_ids.includes(instruction.id));
}

export function validatePlan(plan: CarePlan): CarePlan {
  if (plan.synthetic !== true) throw new Error('This demo only accepts synthetic records.');
  if (!Array.isArray(plan.documents) || !Array.isArray(plan.instructions) || !Array.isArray(plan.conflicts) || !Array.isArray(plan.tasks)) throw new Error('The care plan response is incomplete.');
  if (plan.instructions.some(instruction => !verifiedEvidence(plan, instruction.evidence))) throw new Error('A source quote could not be verified. The care plan was not displayed.');
  if (plan.conflicts.some(conflict => conflict.instruction_ids.some(id => !plan.instructions.some(item => item.id === id)))) throw new Error('A conflict references a missing instruction.');
  return plan;
}
