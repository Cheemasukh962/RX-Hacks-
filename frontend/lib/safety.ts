import type { CarePlan, Evidence, Instruction } from './types';

// Conservative demo guard, not a symptom assessment or a clinical triage system.
export function isUrgent(text: string): boolean {
  return /chest pain|trouble breathing|can(?:not|'t) breathe|difficulty breathing|shortness of breath|sudden (?:vision loss|loss of vision)|lost (?:my )?vision|face droop|slurred speech|stroke|suicid|kill myself|hurt myself|self[- ]harm|dolor (?:en el|de) pecho|no puedo respirar|dificultad para respirar|p[eé]rdida (?:repentina )?de (?:la )?visi[oó]n|derrame cerebral|matarme|hacerme da[ñn]o/i.test(text);
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
