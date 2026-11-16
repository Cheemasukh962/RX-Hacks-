// LOCAL SAMPLE DATA (Demo mode). Shaped like the REXO backend's CarePlan responses.
// Replace with live API calls once the backend is reachable.

export const DOC_LABELS = {
  avs: { en: "After-visit summary", es: "Resumen de la visita" },
  note: { en: "Clinical note", es: "Nota clínica" },
};

export const SAMPLE_CASES = [
  {
    id: "meloxicam",
    featured: true,
    synthetic: false,
    hasAltered: true,
    title: { en: "Back pain visit", es: "Visita por dolor de espalda" },
    blurb: { en: "Meloxicam, a prednisone taper and physical therapy.", es: "Meloxicam, prednisona en dosis decreciente y fisioterapia." },
    tag: { en: "Main demo", es: "Demo principal" },
    summary: {
      en: [
        "Take meloxicam 15 mg with food.",
        "Take the prednisone taper for 10 days, then stop.",
        "Restart physical therapy. You have two visits.",
        "Get a new X-ray of your back.",
        "Go to the ER if you notice the warning signs in your clinical note.",
      ],
      es: [
        "Tome meloxicam 15 mg con comida.",
        "Tome la prednisona en dosis decreciente por 10 días y luego pare.",
        "Retome la fisioterapia. Tiene dos visitas.",
        "Hágase una nueva radiografía de la espalda.",
        "Vaya a urgencias si nota las señales de alerta de su nota clínica.",
      ],
    },
    instructions: [
      { id: "m1", kind: "medication", name: "Meloxicam", amount: "15 mg, 1 tablet", frequency: { en: "Once a day, with food", es: "Una vez al día, con comida" }, duration: null, evidence: { doc: "avs", quote: "Take 1 tablet by mouth daily. Take with food" }, disputedWhenAltered: true, hasRisk: true },
      { id: "m2", kind: "medication", name: "Prednisone", amount: "10 mg tablets: 5, 4, 3, 2, then 1", frequency: { en: "Each step for 2 days", es: "Cada paso por 2 días" }, duration: { en: "10 days, then stop", es: "10 días, luego pare" }, evidence: { doc: "avs", quote: "10-day taper (5→4→3→2→1 tablets, 2 days each, then stop)" } },
      { id: "m3", kind: "medication", name: "Cyclobenzaprine", amount: "10 mg, 1 tablet", frequency: { en: "2 times a day as needed for muscle spasms", es: "2 veces al día según sea necesario para espasmos" }, duration: null, evidence: { doc: "avs", quote: "1 tablet by mouth 2 times a day as needed for muscle spasms" }, disputed: true },
      { id: "m4", kind: "medication", name: "Ketorolac (Toradol)", amount: { en: "Given in clinic", es: "Aplicado en la clínica" }, frequency: null, duration: null, evidence: { doc: "note", quote: "IM Toradol at the time of the visit" } },
      { id: "f1", kind: "follow_up", name: { en: "Physical therapy", es: "Fisioterapia" }, amount: { en: "Two visits", es: "Dos visitas" }, frequency: null, duration: null, evidence: { doc: "note", quote: "reStart physical therapy" } },
      { id: "f2", kind: "lab", name: { en: "New X-ray", es: "Nueva radiografía" }, amount: null, frequency: null, duration: null, evidence: { doc: "note", quote: "get new x-ray to rule out compression fracture" } },
      { id: "w1", kind: "warning_sign", name: { en: "Go to the ER for signs of cauda equina syndrome", es: "Vaya a urgencias si hay señales de síndrome de cauda equina" }, detail: { en: "This means pressure on the nerves at the base of the spine: new numbness between the legs, trouble peeing or controlling your bowels, or sudden leg weakness.", es: "Significa presión en los nervios de la base de la columna: adormecimiento nuevo entre las piernas, problemas para orinar o controlar el intestino, o debilidad repentina en las piernas." }, amount: null, frequency: null, duration: null, evidence: { doc: "note", quote: "go to ER if symptoms of cauda equina syndrome develop" } },
    ],
    findings: [
      { id: "c1", type: "frequency_mismatch", alteredOnly: true, instructionId: "m1", title: { en: "Your documents don't match on how often to take meloxicam.", es: "Sus documentos no coinciden en la frecuencia del meloxicam." }, quotes: [{ doc: "avs", quote: "Take 1 tablet by mouth daily. Take with food" }, { doc: "note", quote: "Take meloxicam 15 mg twice daily", altered: true }] },
      { id: "c2", type: "within_document", instructionId: "m3", title: { en: "One document says two different things about cyclobenzaprine.", es: "Un documento dice dos cosas distintas sobre la ciclobenzaprina." }, quotes: [{ doc: "avs", quote: "Status: Discontinued" }, { doc: "avs", quote: "START taking: 1 tablet by mouth 2 times a day as needed for muscle spasms" }] },
      { id: "c3", type: "only_in_one", instructionId: "w1", title: { en: "Your after-visit summary doesn't mention this warning sign.", es: "Su resumen de la visita no menciona esta señal de alerta." }, quotes: [{ doc: "note", quote: "go to ER if symptoms of cauda equina syndrome develop" }] },
      { id: "c4", type: "only_in_one", instructionId: "f2", title: { en: "Your after-visit summary doesn't mention the X-ray.", es: "Su resumen de la visita no menciona la radiografía." }, quotes: [{ doc: "note", quote: "get new x-ray to rule out compression fracture" }] },
      { id: "c5", type: "worded_differently", instructionId: "m2", title: { en: "Prednisone is worded differently in each document.", es: "La prednisona está redactada de forma distinta en cada documento." }, quotes: [{ doc: "avs", quote: "10-day taper (5→4→3→2→1 tablets, 2 days each, then stop)" }, { doc: "note", quote: "Can also try steroid taper, but doubt radiculitis." }] },
    ],
  },
  {
    id: "eye-drops",
    synthetic: true,
    title: { en: "Eye drops after surgery", es: "Gotas para los ojos tras la cirugía" },
    blurb: { en: "Steroid drops after a corneal transplant.", es: "Gotas con esteroide tras un trasplante de córnea." },
    tag: { en: "How often", es: "Frecuencia" },
    summary: {
      en: ["Use prednisolone drops in your right eye.", "Your documents don't agree on how often.", "Come back for an eye check in 1 week.", "Call right away for eye pain, redness or blurry vision."],
      es: ["Use gotas de prednisolona en el ojo derecho.", "Sus documentos no coinciden en la frecuencia.", "Regrese para una revisión en 1 semana.", "Llame de inmediato si hay dolor, enrojecimiento o visión borrosa."],
    },
    instructions: [
      { id: "e1", kind: "medication", name: "Prednisolone acetate 1% eye drops", amount: { en: "1 drop, right eye", es: "1 gota, ojo derecho" }, frequency: { en: "4 times a day", es: "4 veces al día" }, duration: null, evidence: { doc: "avs", quote: "Prednisolone acetate 1%: 1 drop in the right eye 4 times a day" }, disputed: true, hasRisk: true },
      { id: "e2", kind: "follow_up", name: { en: "Eye check", es: "Revisión del ojo" }, amount: { en: "In 1 week", es: "En 1 semana" }, frequency: null, duration: null, evidence: { doc: "avs", quote: "Return to clinic in 1 week for graft check" } },
      { id: "e3", kind: "warning_sign", name: { en: "Eye pain, redness, light sensitivity or blurry vision", es: "Dolor, enrojecimiento, sensibilidad a la luz o visión borrosa" }, amount: null, frequency: null, duration: null, evidence: { doc: "note", quote: "Call immediately for pain, redness, photophobia or decreased vision" } },
    ],
    findings: [
      { id: "c1", type: "frequency_mismatch", instructionId: "e1", title: { en: "Your documents don't match on how often to use the drops.", es: "Sus documentos no coinciden en la frecuencia de las gotas." }, quotes: [{ doc: "avs", quote: "Prednisolone acetate 1%: 1 drop in the right eye 4 times a day" }, { doc: "note", quote: "Pred acetate 1% OD every 2 hours while awake" }] },
    ],
  },
  {
    id: "blood-pressure",
    synthetic: true,
    title: { en: "Blood pressure", es: "Presión arterial" },
    blurb: { en: "A dose change and a pain reliever question.", es: "Un cambio de dosis y una duda sobre un analgésico." },
    tag: { en: "Dose + continue or avoid", es: "Dosis + continuar o evitar" },
    summary: {
      en: ["Take lisinopril once a day.", "Your documents don't agree on the dose.", "They also disagree about ibuprofen.", "Check your blood pressure at home and bring the numbers."],
      es: ["Tome lisinopril una vez al día.", "Sus documentos no coinciden en la dosis.", "Tampoco coinciden sobre el ibuprofeno.", "Mida su presión en casa y traiga los números."],
    },
    instructions: [
      { id: "b1", kind: "medication", name: "Lisinopril", amount: "20 mg", frequency: { en: "Once a day", es: "Una vez al día" }, duration: null, evidence: { doc: "avs", quote: "Lisinopril 20 mg tablet: take 1 tablet once daily" }, disputed: true, hasRisk: true },
      { id: "b2", kind: "medication", name: "Ibuprofen", amount: null, frequency: { en: "As needed", es: "Según sea necesario" }, duration: null, evidence: { doc: "avs", quote: "Continue ibuprofen as needed for knee pain" }, disputed: true },
      { id: "b3", kind: "follow_up", name: { en: "Home blood pressure log", es: "Registro de presión en casa" }, amount: { en: "Bring it in 4 weeks", es: "Tráigalo en 4 semanas" }, frequency: null, duration: null, evidence: { doc: "note", quote: "Home BP log, recheck in 4 weeks" } },
    ],
    findings: [
      { id: "c1", type: "dose_mismatch", instructionId: "b1", title: { en: "Your documents don't match on the lisinopril dose.", es: "Sus documentos no coinciden en la dosis de lisinopril." }, quotes: [{ doc: "avs", quote: "Lisinopril 20 mg tablet: take 1 tablet once daily" }, { doc: "note", quote: "Increase lisinopril to 40 mg daily" }] },
      { id: "c2", type: "action_mismatch", instructionId: "b2", title: { en: "Your documents don't match on ibuprofen.", es: "Sus documentos no coinciden sobre el ibuprofeno." }, quotes: [{ doc: "avs", quote: "Continue ibuprofen as needed for knee pain" }, { doc: "note", quote: "Avoid NSAIDs including ibuprofen" }] },
    ],
  },
  {
    id: "antibiotic",
    synthetic: true,
    title: { en: "Antibiotic course", es: "Tratamiento con antibiótico" },
    blurb: { en: "Amoxicillin for a sinus infection.", es: "Amoxicilina para una infección sinusal." },
    tag: { en: "How long", es: "Duración" },
    summary: {
      en: ["Take amoxicillin 500 mg 3 times a day.", "Your documents don't agree on how many days.", "Call if you are not better in 3 days."],
      es: ["Tome amoxicilina 500 mg 3 veces al día.", "Sus documentos no coinciden en cuántos días.", "Llame si no mejora en 3 días."],
    },
    instructions: [
      { id: "a1", kind: "medication", name: "Amoxicillin", amount: "500 mg", frequency: { en: "3 times a day", es: "3 veces al día" }, duration: { en: "10 days", es: "10 días" }, evidence: { doc: "avs", quote: "Amoxicillin 500 mg: take 1 capsule 3 times a day for 10 days" }, disputed: true, hasRisk: true },
      { id: "a2", kind: "warning_sign", name: { en: "Rash, swelling or trouble breathing", es: "Sarpullido, hinchazón o dificultad para respirar" }, amount: null, frequency: null, duration: null, evidence: { doc: "avs", quote: "Stop and seek care for rash, swelling, or trouble breathing" } },
    ],
    findings: [
      { id: "c1", type: "duration_mismatch", instructionId: "a1", title: { en: "Your documents don't match on how long to take amoxicillin.", es: "Sus documentos no coinciden en la duración de la amoxicilina." }, quotes: [{ doc: "avs", quote: "Amoxicillin 500 mg: take 1 capsule 3 times a day for 10 days" }, { doc: "note", quote: "Amoxicillin 500 mg TID x 7 days" }] },
    ],
  },
  {
    id: "control",
    synthetic: true,
    title: { en: "Matching documents", es: "Documentos que coinciden" },
    blurb: { en: "A diabetes visit where both documents agree.", es: "Una visita de diabetes donde ambos documentos coinciden." },
    tag: { en: "No differences", es: "Sin diferencias" },
    summary: {
      en: ["Take metformin 500 mg twice a day with meals.", "Get an A1C blood test in 3 months.", "Your two documents agree."],
      es: ["Tome metformina 500 mg dos veces al día con las comidas.", "Hágase un análisis de A1C en 3 meses.", "Sus dos documentos coinciden."],
    },
    instructions: [
      { id: "d1", kind: "medication", name: "Metformin", amount: "500 mg", frequency: { en: "Twice a day with meals", es: "Dos veces al día con las comidas" }, duration: null, evidence: { doc: "avs", quote: "Metformin 500 mg: take 1 tablet twice daily with meals" } },
      { id: "d2", kind: "lab", name: { en: "A1C blood test", es: "Análisis de sangre A1C" }, amount: { en: "In 3 months", es: "En 3 meses" }, frequency: null, duration: null, evidence: { doc: "note", quote: "Repeat A1C in 3 months" } },
    ],
    findings: [],
  },
];

export const getCase = (id) => SAMPLE_CASES.find((c) => c.id === id);