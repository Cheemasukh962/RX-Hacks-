// DEMO MODE chat: scripted, sourced answers standing in for POST /api/chat.
import { DOC_LABELS } from "@/lib/sampleCases";
import { loc } from "@/lib/loc";

const URGENT = [/chest pain/, /can'?t breathe/, /trouble breathing/, /vomiting blood/, /black stool/, /bloody stool/, /slurred/, /suicid/, /dolor (de|en el) pecho/, /no puedo respirar/, /vomit\w* sangre/, /heces negras/];
export const isUrgent = (text) => URGENT.some((re) => re.test(text.toLowerCase()));

const LABEL_SOURCE = "FDA drug label (openFDA) · MedlinePlus";

const MELOXICAM_RULES = [
  { test: /empty stomach|food|eat|comida|estómago vacío|comer/, quoteId: "m1",
    en: "Meloxicam can irritate the stomach. Taking it with food helps protect your stomach. On an empty stomach you are more likely to get stomach pain or upset.",
    es: "El meloxicam puede irritar el estómago. Tomarlo con comida ayuda a protegerlo. Con el estómago vacío es más probable tener dolor o malestar." },
  { test: /ibuprofen|advil|motrin|naproxen|aleve|ibuprofeno|naproxeno/,
    en: "Ibuprofen and naproxen are the same kind of medicine as meloxicam (NSAIDs). The label says taking them together raises the risk of stomach bleeding. Ask your pharmacist or doctor before adding one.",
    es: "El ibuprofeno y el naproxeno son el mismo tipo de medicina que el meloxicam (AINE). La etiqueta dice que tomarlos juntos aumenta el riesgo de sangrado en el estómago. Pregunte a su farmacéutico o médico antes de añadir uno." },
  { test: /prednison/, quoteId: "m2", offerEmail: true,
    en: "The label says taking meloxicam with a steroid like prednisone raises the risk of stomach bleeding. Taking meloxicam with food helps. Watch for black or bloody stools or stomach pain. Your doctor prescribed both for you. If you are still unsure, I can draft an email, or you can ask your pharmacist.",
    es: "La etiqueta dice que tomar meloxicam con un esteroide como la prednisona aumenta el riesgo de sangrado en el estómago. Tomarlo con comida ayuda. Esté atento a heces negras o con sangre o dolor de estómago. Su médico le recetó ambos. Si aún tiene dudas, puedo redactar un correo, o puede preguntar a su farmacéutico." },
  { test: /miss|forgot|forget|olvid|me salt/,
    en: "General guidance: take it when you remember. If it is almost time for your next one, take just that next one at the usual time. Do not take two at once.",
    es: "Guía general: tómelo cuando se acuerde. Si ya casi es hora de la siguiente dosis, tome solo esa a la hora habitual. No tome dos a la vez." },
  { test: /side effect|efectos/,
    en: "Common side effects are stomach upset, nausea, diarrhea and dizziness. The label also warns about serious risks: heart attack or stroke, and stomach bleeding or ulcers. Get help right away for black or bloody stools, vomiting blood, chest pain, shortness of breath, weakness on one side or slurred speech.",
    es: "Los efectos comunes son malestar de estómago, náuseas, diarrea y mareo. La etiqueta también advierte riesgos graves: infarto o derrame cerebral, y sangrado o úlceras en el estómago. Busque ayuda de inmediato si hay heces negras o con sangre, vómito con sangre, dolor de pecho, falta de aire, debilidad en un lado o dificultad para hablar." },
  { test: /what (does|is)|used for|what's it for|para qué|qué es|qué hace/, quoteId: "m1",
    en: "Meloxicam is an NSAID. It is a medicine for pain and inflammation.",
    es: "El meloxicam es un AINE. Es una medicina para el dolor y la inflamación." },
];

const quoteOf = (data, id) => data.instructions.find((i) => i.id === id)?.evidence;

export function answer(data, text, lang, altered) {
  const q = text.toLowerCase();
  const findings = data.findings.filter((f) => !f.alteredOnly || altered);
  const conflict = findings.find((f) => f.quotes.length === 2 && f.type !== "worded_differently");

  if (conflict && /which|right|correct|cuál|twice|dos veces/.test(q)) {
    const says = conflict.quotes.map((x) => `${DOC_LABELS[x.doc][lang]}: "${x.quote}"`).join(" ");
    return {
      tag: "documents", finding: conflict, offerEmail: true,
      text: lang === "es"
        ? `Sus documentos dicen dos cosas distintas. ${says} No puedo decirle cuál aplica a usted. Su médico debe confirmarlo.`
        : `Your documents say two different things. ${says} I can't tell you which one applies to you. Your doctor needs to confirm.`,
      general: data.id === "meloxicam" && conflict.type === "frequency_mismatch"
        ? { text: lang === "es" ? "La etiqueta indica que lo habitual es una vez al día." : "The label's usual schedule is once a day.", source: LABEL_SOURCE }
        : null,
    };
  }

  if (data.id === "meloxicam") {
    const rule = MELOXICAM_RULES.find((r) => r.test.test(q));
    if (rule) {
      const evidence = rule.quoteId ? quoteOf(data, rule.quoteId) : null;
      return { tag: "general", text: rule[lang], source: LABEL_SOURCE, quotes: evidence ? [evidence] : [], offerEmail: !!rule.offerEmail };
    }
  }

  const mentioned = data.instructions.find((i) =>
    [loc(i.name, "en"), loc(i.name, "es")].join(" ").toLowerCase().split(/[^a-záéíóúñ]+/).some((w) => w.length >= 5 && q.includes(w))
  );
  if (mentioned) {
    return {
      tag: "documents", quotes: [mentioned.evidence],
      text: lang === "es" ? `Esto es lo que dicen sus documentos sobre ${loc(mentioned.name, lang)}.` : `Here is what your documents say about ${loc(mentioned.name, lang)}.`,
    };
  }

  return {
    tag: "unclear", offerEmail: true,
    text: lang === "es"
      ? "Esto no está en sus documentos ni en mis referencias. ¿Quiere que redacte un correo para su médico? También puede preguntar a su farmacéutico."
      : "This isn't in your documents or my references. Want me to draft an email to your doctor? You can also ask your pharmacist.",
  };
}