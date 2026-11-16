// Turns REXO backend responses (CarePlan + insights + demo-altered case) into the shape the UI uses
// (the same shape as src/lib/sampleCases.js). Facts are never invented here: missing values stay null.
const DOC_KIND = { after_visit_summary: "avs", clinical_note: "note" };

const FREQ = {
  1: { en: "Once a day", es: "Una vez al día" },
  2: { en: "Twice a day", es: "Dos veces al día" },
  3: { en: "3 times a day", es: "3 veces al día" },
  4: { en: "4 times a day", es: "4 veces al día" },
};
const KIND_NAME = {
  follow_up: { en: "Follow-up", es: "Seguimiento" },
  lab: { en: "Test or order", es: "Prueba u orden" },
  lifestyle: { en: "Self-care", es: "Cuidado personal" },
  warning_sign: { en: "Warning sign", es: "Señal de alerta" },
  supply: { en: "Supplies", es: "Suministros" },
};
const CONFLICT_TITLE = {
  dose_mismatch: { en: (n) => `Your documents don't match on the ${n} dose.`, es: (n) => `Sus documentos no coinciden en la dosis de ${n}.` },
  frequency_mismatch: { en: (n) => `Your documents don't match on how often to take ${n}.`, es: (n) => `Sus documentos no coinciden en la frecuencia de ${n}.` },
  duration_mismatch: { en: (n) => `Your documents don't match on how long to take ${n}.`, es: (n) => `Sus documentos no coinciden en la duración de ${n}.` },
  action_mismatch: { en: (n) => `Your documents don't match on whether to keep taking ${n}.`, es: (n) => `Sus documentos no coinciden en si seguir con ${n}.` },
  date_mismatch: { en: (n) => `Your documents don't match on the date for ${n}.`, es: (n) => `Sus documentos no coinciden en la fecha de ${n}.` },
};
// Medicines with prepared "Why it matters" cards (src/lib/riskCards.js keys).
const RISK_KEYS = [[/meloxicam|mobic/i, "meloxicam"], [/prednisolone/i, "eye-drops"], [/amoxicillin/i, "antibiotic"]];

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

export const riskKeyFor = (name) => (RISK_KEYS.find(([re]) => re.test(name || "")) || [])[1] || null;

function docKinds(plan) {
  return Object.fromEntries(plan.documents.map((d) => [d.id, DOC_KIND[d.type] || "note"]));
}

function evidence(ev, kinds, alteredTexts = []) {
  return { doc: kinds[ev.document_id] || "note", quote: ev.quote, altered: alteredTexts.some((t) => ev.quote.includes(t)) || undefined };
}

function instructionToUi(i, kinds) {
  const name = i.kind === "medication" ? cap(i.medication_name) || { en: "Medicine", es: "Medicina" } : KIND_NAME[i.kind] || cap(i.kind);
  const amount = [i.strength, i.dose].filter(Boolean).join(", ") || null;
  const freq = i.frequency_per_day ? FREQ[i.frequency_per_day] || { en: `${i.frequency_per_day} times a day`, es: `${i.frequency_per_day} veces al día` } : null;
  return {
    id: i.id,
    kind: i.kind,
    name,
    amount: i.kind === "medication" ? amount : i.due || null,
    frequency: freq,
    duration: i.duration || null,
    detail: i.kind !== "medication" ? { en: i.evidence.quote, es: i.evidence.quote } : undefined,
    evidence: evidence(i.evidence, kinds),
    hasRisk: i.kind === "medication" && Boolean(riskKeyFor(i.medication_name)),
    medicationName: i.medication_name || null,
  };
}

function conflictsToFindings(plan, kinds, { alteredOnly = false, alteredTexts = [] } = {}) {
  const byId = Object.fromEntries(plan.instructions.map((i) => [i.id, i]));
  return plan.conflicts.map((c) => {
    const items = c.instruction_ids.map((id) => byId[id]).filter(Boolean);
    const med = items.find((i) => i.medication_name)?.medication_name || "this medicine";
    const title = CONFLICT_TITLE[c.type] || CONFLICT_TITLE.dose_mismatch;
    return {
      id: `${alteredOnly ? "alt-" : ""}${c.id}`,
      type: c.type,
      alteredOnly,
      instructionId: items[0]?.id,
      medicationName: med,
      title: { en: title.en(med), es: title.es(med) },
      quotes: items.map((i) => evidence(i.evidence, kinds, alteredTexts)),
    };
  });
}

function insightFindings(insights, kinds) {
  return (insights?.findings || []).map((f) => ({
    id: f.id,
    type: f.type,
    instructionId: f.instruction_id || undefined,
    title: f.title,
    quotes: f.quotes.map((q) => evidence(q, kinds)),
  }));
}

/** Build the UI case from the backend plan, its insights, and (optionally) the demo-altered plan. */
export function toUiCase(plan, insights, altered, meta = {}) {
  const kinds = docKinds(plan);
  const instructions = plan.instructions.map((i) => instructionToUi(i, kinds));
  const findings = [...conflictsToFindings(plan, kinds), ...insightFindings(insights, kinds)];

  if (altered) {
    const altKinds = docKinds(altered);
    const alteredTexts = (altered.altered || []).map((a) => a.text);
    const altFindings = conflictsToFindings(altered, altKinds, { alteredOnly: true, alteredTexts })
      .filter((f) => f.quotes.some((q) => q.altered));
    findings.push(...altFindings);
    const disputedMeds = new Set(altFindings.map((f) => (f.medicationName || "").toLowerCase()));
    instructions.forEach((i) => {
      if (i.medicationName && disputedMeds.has(i.medicationName.toLowerCase())) i.disputedWhenAltered = true;
    });
  }
  const disputed = new Set(plan.conflicts.flatMap((c) => c.instruction_ids));
  instructions.forEach((i) => { if (disputed.has(i.id)) i.disputed = true; });

  const firstRisk = plan.instructions.map((i) => riskKeyFor(i.medication_name)).find(Boolean) || null;
  return {
    id: plan.case_id,
    live: true,
    mode: plan.mode,
    synthetic: Boolean(meta.synthetic),
    hasAltered: Boolean(altered),
    title: meta.title || { en: "Your visit", es: "Su visita" },
    summary: insights?.summary || { en: [], es: [] },
    instructions,
    findings,
    riskKey: firstRisk,
    caseId: plan.case_id,
    alteredCaseId: altered?.case_id || null,
  };
}
