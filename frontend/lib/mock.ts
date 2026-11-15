import { demoCases, fixtureTexts } from './fixtures';
import { hasConflict, isUrgent, redactText, validatePlan } from './safety';
import type { BarrierResult, CarePlan, CaseInput, Conflict, Evidence, FeedbackInput, Instruction, PatientProfile, Style, TeachbackResult } from './types';

type State = { plans: Record<string, CarePlan>; profiles: Record<string, PatientProfile> };
let memory: State = { plans: {}, profiles: {} };
const storageKey = 'rexo-demo-v1';
function state(): State {
  if (typeof window !== 'undefined') {
    try { const saved = sessionStorage.getItem(storageKey); if (saved) memory = JSON.parse(saved); } catch { /* In-memory fallback for blocked storage. */ }
  }
  return memory;
}
function save() { if (typeof window !== 'undefined') { try { sessionStorage.setItem(storageKey, JSON.stringify(memory)); } catch { /* Current tab still works. */ } } }
export function newProfile(input: Partial<PatientProfile> = {}): PatientProfile {
  return { profile_id: 'p-A', language: 'en', detail: 'brief', modes: ['read'], context_opt_in: '', term_scores: {}, style_bandit: { brief: [1, 1], detailed: [1, 1], analogy: [1, 1], audio: [1, 1], visual: [1, 1] }, teach_back_history: [], concerns: [], ...input, mode: 'demo' };
}
const numberWords: Record<string, number> = { one: 1, two: 2, three: 3, four: 4, once: 1, twice: 2, una: 1, uno: 1, un: 1, dos: 2, tres: 3, cuatro: 4 };
function numeric(value: string) { return numberWords[value.toLowerCase()] ?? Number(value); }
function frequency(text: string): number | null {
  const match = text.match(/(\d+|one|two|three|four|una|dos|tres|cuatro)\s+(?:times? (?:a day|daily|per day)|veces (?:al|por) d[ií]a)/i);
  if (match) return numeric(match[1]);
  if (/twice daily|twice a day/i.test(text)) return 2;
  if (/once daily|once a day|una vez al d[ií]a|\b(?:mg )?daily\b/i.test(text)) return 1;
  return null;
}

// Deliberately narrow fixture parser. Unrecognized text is never replaced by a sample case.
export function buildDemoPlan(input: CaseInput): CarePlan {
  const source = 'demo_case_id' in input ? fixtureTexts[input.demo_case_id] : input.documents;
  if (!source) throw new Error('This sample case is not available.');
  if (!source.length || source.every(doc => !doc.text.trim())) throw new Error('Paste at least one synthetic document.');
  const documents = source.filter(doc => doc.text.trim()).map((doc, index) => {
    const type = doc.type_hint ?? (/clinical note/i.test(doc.text) ? 'clinical_note' : 'after_visit_summary');
    return { id: `${type === 'clinical_note' ? 'note' : 'avs'}-${index + 1}`, type, title: type === 'clinical_note' ? 'Sample Clinical Note' : 'Sample After-Visit Summary', text: redactText(doc.text).text };
  });
  const instructions: Instruction[] = [];
  for (const doc of documents) {
    for (const line of doc.text.split(/\n/).map(text => text.trim()).filter(Boolean)) {
      const medicine = /prednisolone|lisinopril|ibuprofen|NSAIDs/i.exec(line);
      // Only instruction-like lines; headings, quoted prompt injection, and general prose are not orders.
      const medication = medicine && /^(?:use|take|continue|avoid|stop|start)\b/i.test(line);
      const followup = /^follow[- ]up visit on /i.test(line);
      const warning = /^call your care team /i.test(line);
      if (!medication && !followup && !warning) continue;
      const isEye = /prednisolone/i.test(line);
      const isLisinopril = /lisinopril/i.test(line);
      const doseMatch = line.match(/(\d+(?:\.\d+)?|one|two)\s*(mg|drops?)\b/i);
      const duration = line.match(/for (\d+|one|two|three|four) (days?|weeks?)/i);
      const action = /^(start|continue|stop|avoid|change)\b/i.exec(line)?.[1]?.toLowerCase() as Instruction['action'] | undefined;
      instructions.push({ id: `i-${instructions.length + 1}`, kind: medication ? 'medication' : followup ? 'follow_up' : 'warning_sign', medication_name: medication ? isEye ? 'prednisolone acetate ophthalmic suspension' : isLisinopril ? 'lisinopril' : /ibuprofen/i.test(line) ? 'ibuprofen' : 'NSAIDs' : null, strength: medication ? line.match(/\d+(?:\.\d+)?%/)?.[0] ?? null : null, dose: medication && doseMatch ? `${numeric(doseMatch[1])} ${doseMatch[2].toLowerCase().replace('drops', 'drop')}` : null, route: medication && /eye|ophthalmic/i.test(line) ? 'ophthalmic' : null, frequency_per_day: medication ? frequency(line) : null, duration: duration ? `${numeric(duration[1])} ${duration[2]}` : null, action: action ?? null, refills: null, quantity: null, due: followup ? line.replace(/^follow[- ]up visit on /i, '').replace(/\.$/, '') : null, evidence: { document_id: doc.id, quote: line } });
    }
  }
  const conflicts: Conflict[] = [];
  for (let a = 0; a < instructions.length; a++) for (let b = a + 1; b < instructions.length; b++) {
    const left = instructions[a], right = instructions[b];
    if (left.evidence.document_id === right.evidence.document_id || left.kind !== right.kind) continue;
    const namesMatch = left.medication_name === right.medication_name || [left.medication_name, right.medication_name].every(name => name === 'ibuprofen' || name === 'NSAIDs');
    if (left.kind === 'medication' && !namesMatch) continue;
    if (left.kind !== 'medication' && left.kind !== 'follow_up') continue;
    const fields = [['dose', 'dose_mismatch'], ['frequency_per_day', 'frequency_mismatch'], ['action', 'action_mismatch'], ['due', 'date_mismatch'], ['duration', 'duration_mismatch']] as const;
    for (const [field, type] of fields) {
      if (left[field] === null || right[field] === null || left[field] === right[field]) continue;
      if (field === 'action' && ![left.action, right.action].some(value => value === 'stop' || value === 'avoid')) continue;
      conflicts.push({ id: `c${conflicts.length + 1}`, type, instruction_ids: [left.id, right.id], level: left.medication_name !== right.medication_name ? 'potential_conflict' : 'confirmed_conflict', resolved: false });
    }
  }
  const plan: CarePlan = { mode: 'demo', synthetic: true, case_id: 'demo_case_id' in input ? input.demo_case_id : `demo-pasted-${Date.now()}`, documents, instructions, conflicts, tasks: [] };
  // Deduplicate only identical, non-conflicting instructions from the two documents.
  const seen = new Set<string>();
  plan.tasks = instructions.filter(item => {
    const key = `${item.kind}:${item.medication_name}:${item.evidence.quote}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return item.kind !== 'warning_sign';
  }).map(item => ({ id: `task-${item.id}`, instruction_id: item.id, label: item.medication_name ?? 'Follow-up visit', status: hasConflict(plan, item) ? 'needs_clarification' : 'open' }));
  return validatePlan(plan);
}

export function checkTeachback(plan: CarePlan, instruction: Instruction, text: string, spanish = false): TeachbackResult {
  const base = { mode: 'demo' as const, confidence: 0, slot_check: { dose: null, frequency: null, duration: null } as TeachbackResult['slot_check'], pathway: 'rules' as const };
  if (hasConflict(plan, instruction)) return { ...base, labels: ['source_conflict'], source_conflict: true, feedback_text: spanish ? 'Tus documentos no coinciden. Pide al equipo médico que aclare las instrucciones; no podemos confirmar una frecuencia.' : 'Your documents disagree. Ask your care team to clarify the instructions; we cannot confirm a schedule.' };
  if (isUrgent(text)) return { ...base, labels: ['uncertain'], source_conflict: false, feedback_text: spanish ? 'Llama al 911 o a tu equipo médico ahora.' : 'Call 911 or your care team now.' };
  const labels: string[] = [];
  const saidFrequency = frequency(text);
  const saidDose = text.match(/(\d+(?:\.\d+)?|one|two|una|un|dos)\s*(mg|drops?|gotas?)\b/i);
  const saidDuration = text.match(/(?:for|durante) (\d+|one|two|three|four|uno|dos|tres|cuatro) (days?|weeks?|d[ií]as?|semanas?)/i);
  if (saidFrequency !== null && instruction.frequency_per_day !== null) base.slot_check.frequency = saidFrequency === instruction.frequency_per_day;
  if (saidDose && instruction.dose) base.slot_check.dose = `${numeric(saidDose[1])} ${saidDose[2].toLowerCase().replace(/drops|gotas?/, 'drop')}` === instruction.dose;
  if (saidDuration && instruction.duration) base.slot_check.duration = `${numeric(saidDuration[1])} ${saidDuration[2].toLowerCase().replace(/d[ií]as?/, 'days').replace(/semanas?/, 'weeks')}` === instruction.duration;
  if (base.slot_check.dose === false) labels.push('dose_error');
  if (base.slot_check.frequency === false) labels.push('frequency_error');
  if (base.slot_check.duration === false) labels.push('duration_error');
  if (/\b(stop|stopping|dejar|suspender)\b/i.test(text) && !/\b(?:not|never|don't|won't|no)\b/i.test(text) && instruction.action !== 'stop') labels.push('stop_negation');
  const uncertain = /\?|\b(?:maybe|unsure|not sure|don't know|quiz[aá]s|no s[eé])\b/i.test(text);
  const hasKnownFact = instruction.dose !== null || instruction.frequency_per_day !== null || instruction.duration !== null;
  const allKnownChecked = (instruction.dose === null || base.slot_check.dose === true) && (instruction.frequency_per_day === null || base.slot_check.frequency === true) && (instruction.duration === null || base.slot_check.duration === true);
  if (!labels.length) labels.push(!uncertain && hasKnownFact && allKnownChecked ? 'understood' : 'uncertain');
  const understood = labels.includes('understood');
  return { ...base, labels, source_conflict: false, feedback_text: understood ? spanish ? 'Los datos que mencionaste coinciden con la cita. Esta comprobación de reglas no mide la comprensión clínica.' : 'The facts you mentioned match the quote. This rules check does not measure clinical comprehension.' : labels.includes('uncertain') ? spanish ? 'No hay suficiente información para comprobarlo. Compara tu respuesta con la cita del documento.' : 'There is not enough information to check this. Compare your answer with the document quote.' : spanish ? 'Tu respuesta difiere de la cita. Revisa los datos señalados y pide ayuda al equipo médico si algo no está claro.' : 'Your answer differs from the source quote. Review the flagged facts, and ask your care team if anything is unclear.' };
}

export function classifyBarrier(text: string, spanish = false): BarrierResult {
  const urgent = isUrgent(text);
  const rules: [string, RegExp][] = [ ['side_effect', /gritty|side effect|irritat|nause|arenos|efecto secundario/i], ['cost', /cost|expensive|afford|caro|costo|dinero/i], ['ran_out_refill', /ran out|refill|se acab|recarga/i], ['forgot', /forgot|forget|olvid/i], ['schedule_conflict', /schedule|shift|horario|turno/i], ['doesnt_see_importance', /why.*need|don't need|no.*necesit/i], ['confusion', /confus|understand|entiendo/i], ['wants_to_stop', /stop|stopping|dejar|suspender/i] ];
  const labels = urgent ? [] : rules.filter(([, pattern]) => pattern.test(text)).map(([label]) => label);
  if (!urgent && !labels.length) labels.push('uncertain');
  return { mode: 'demo', labels, confirm_prompt: spanish ? '¿Estas etiquetas describen tu preocupación? Puedes cambiarlas.' : 'Do these labels describe your concern? You can change them.', urgent, support_text: urgent ? spanish ? 'Llama al 911 o a tu equipo médico ahora.' : 'Call 911 or your care team now.' : spanish ? 'Gracias por contarlo. Comunícate pronto con tu médico o farmacéutico para hablar de tu preocupación. Podemos ayudarte a escribir el mensaje.' : 'Thank you for sharing this. Contact your clinician or pharmacist promptly to discuss your concern. We can help you put it into words.', example_id: `example-${Date.now()}` };
}

export async function mockRequest(path: string, method = 'GET', body?: unknown): Promise<unknown> {
  const current = state();
  const data = (body ?? {}) as Record<string, unknown>;
  const profileId = String(data.profile_id ?? path.split('/')[2] ?? 'p-A');
  const profile = current.profiles[profileId] ?? newProfile({ profile_id: profileId });
  const spanish = profile.language === 'es';
  const plan = current.plans[String(data.case_id)];
  const instruction = plan?.instructions.find(item => item.id === data.instruction_id);
  let result: unknown;
  if (path === '/demo-cases') return structuredClone(demoCases);
  if (path === '/cases' && method === 'POST') {
    const created = buildDemoPlan(body as CaseInput); current.plans[created.case_id] = created; result = created;
  } else if (path.startsWith('/cases/')) {
    result = current.plans[decodeURIComponent(path.split('/')[2])];
    if (!result) throw new Error('This case is no longer in this session. Please select a sample again.');
  } else if (path === '/profile' || path.startsWith('/profile/')) {
    const reset = path.endsWith('/reset');
    const next = reset ? newProfile({ profile_id: profileId }) : method === 'GET' ? profile : newProfile({ ...profile, ...data });
    current.profiles[next.profile_id] = next; result = next;
  } else if (path === '/explain') {
    if (!plan || !instruction) throw new Error('Choose an instruction first.');
    const style = (data.style_override ?? profile.detail) as Style;
    const related = hasConflict(plan, instruction) ? plan.conflicts.filter(c => c.instruction_ids.includes(instruction.id)).flatMap(c => c.instruction_ids).map(id => plan.instructions.find(item => item.id === id)!).filter(Boolean) : [instruction];
    const citations = Array.from(new Map(related.map(item => [item.id, item.evidence])).values());
    const conflict = hasConflict(plan, instruction);
    const text = conflict ? spanish ? 'Los documentos dan instrucciones diferentes. Pide a tu equipo médico que las aclare. Las dos citas se muestran completas.' : 'The documents give different instructions. Ask your care team to clarify them. Both source quotes are shown in full.' : spanish ? 'Esta es la instrucción que aparece en tu documento. La cita conserva todos los datos originales.' : 'This is the instruction recorded in your document. The source quote preserves all of the original facts.';
    const extra = style === 'detailed' ? spanish ? ' Si falta un dato, lo mostramos como desconocido. Puedes copiar cualquier pregunta en tu mensaje al equipo médico.' : ' When a detail is missing, we show it as unknown. You can bring any questions into your message to the care team.' : '';
    const terms = [ ['inflammation', 'Inflammation means swelling and irritation.'], ['graft rejection', 'Graft rejection means the body attacks the transplanted tissue.'] ].filter(([term, quote]) => (profile.term_scores[term] ?? 0) < 0.7 && plan.documents.some(doc => doc.text.includes(quote)));
    for (const [, quote] of terms) { const doc = plan.documents.find(doc => doc.text.includes(quote))!; citations.push({ document_id: doc.id, quote }); }
    result = { mode: 'demo', text: text + extra, style, why_this_style: spanish ? 'Usamos tu preferencia explícita. La selección adaptativa requiere el backend.' : 'Using your stated preference. Adaptive style selection requires the backend.', defined_terms: terms.map(([term, definition]) => ({ term, definition })), citations, fact_check: { passed: true, unsupported: [] } };
  } else if (path === '/teachback') {
    if (!plan || !instruction) throw new Error('Choose an instruction first.');
    result = checkTeachback(plan, instruction, String(data.response_text), spanish);
    profile.teach_back_history.push({ instruction_id: instruction.id, response_text: data.response_text, result });
    current.profiles[profileId] = profile;
  } else if (path === '/barrier') {
    result = classifyBarrier(String(data.text), spanish);
  } else if (path === '/feedback') {
    const input = body as FeedbackInput;
    const payload = input.payload;
    if (input.kind === 'term_tap' && typeof payload.term === 'string') profile.term_scores[payload.term] = Math.max(0, (profile.term_scores[payload.term] ?? 0.5) - 0.2);
    if (input.kind === 'style_change' && (payload.style === 'brief' || payload.style === 'detailed')) profile.detail = payload.style;
    if (input.kind === 'thumbs') { const style = String(payload.style) as Style; if (profile.style_bandit[style]) profile.style_bandit[style][(payload.up ?? payload.helpful) ? 0 : 1] += 0.3; }
    if ((input.kind === 'label_confirm' || input.kind === 'label_correct') && typeof payload.text === 'string' && !profile.concerns.includes(payload.text)) profile.concerns.push(payload.text);
    current.profiles[profileId] = profile;
    result = { mode: 'demo', profile, model_updated: false };
  } else if (path === '/ask') {
    if (!plan) throw new Error('Load a care plan first.');
    const urgent = isUrgent(String(data.question));
    // Seeded mode never invents answers to arbitrary questions.
    result = { mode: 'demo', answer: urgent ? spanish ? 'Llama al 911 o a tu equipo médico ahora.' : 'Call 911 or your care team now.' : spanish ? 'El modo de demostración no puede responder preguntas abiertas. Revisa las citas o guarda tu pregunta para el equipo médico.' : 'Seeded mode cannot answer open-ended questions. Review the source quotes or add your question to the care-team message.', citations: [], in_documents: false, urgent };
  } else if (path === '/briefing') {
    if (!plan) throw new Error('Load a care plan first.');
    const include = data.include as { concerns: string[]; conflicts: string[] };
    const conflicts = plan.conflicts.filter(item => include.conflicts.includes(item.id));
    const citations: Evidence[] = conflicts.flatMap(conflict => conflict.instruction_ids.map(id => plan.instructions.find(item => item.id === id)!.evidence));
    const quotes = citations.map(item => `[${item.document_id}] “${item.quote}”`).join('\n');
    const concerns = include.concerns.map(item => `• ${item}`).join('\n');
    const draft_en = `Hello care team,\n\n${concerns ? `I would like to discuss these concerns:\n${concerns}\n\n` : ''}${quotes ? `My documents contain different instructions:\n${quotes}\n\nCould you clarify which instructions I should follow?\n\n` : ''}Please help me understand my next steps. Thank you.\n\n[Synthetic demo record]`;
    const draft_es = `Hola, equipo médico:\n\n${concerns ? `Quisiera hablar de estas preocupaciones (mis propias palabras):\n${concerns}\n\n` : ''}${quotes ? `Mis documentos tienen instrucciones diferentes (citas originales):\n${quotes}\n\n¿Podrían aclarar qué instrucciones debo seguir?\n\n` : ''}Por favor, ayúdenme a entender los siguientes pasos. Gracias.\n\n[Registro de demostración sintético]`;
    result = { mode: 'demo', draft_en, draft_patient_language: spanish ? draft_es : draft_en, citations };
  } else if (path === '/eval') {
    result = { mode: 'demo', status: 'not_run', message: 'No saved backend evaluation has been loaded. Frontend rule tests are separate from the held-out ML benchmark.', eval_results: null, bandit_sim: null };
  } else if (path === '/demo/reset') { memory = { plans: {}, profiles: {} }; result = { mode: 'demo', ok: true }; }
  else if (path === '/voice/transcribe' || path === '/ingest/photo') throw new Error('This feature needs the connected backend. You can type or paste text instead.');
  else throw new Error(`Demo route is unavailable: ${method} ${path}`);
  save();
  return structuredClone(result);
}
