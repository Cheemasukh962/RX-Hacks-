// LOCAL SAMPLE DATA (Demo mode). Captions must come from vetted facts before real use.
const IMG = "https://media.base44.com/images/public/6afa4cb44fe8de88eb21169e/";

export const RISK_CARDS = {
  meloxicam: {
    medicine: "Meloxicam",
    source: "FDA drug label (openFDA) · MedlinePlus",
    cards: [
      { image: IMG + "f13dddc7e_generated_image.png", alt: { en: "A person at a table with a meal, holding one tablet.", es: "Una persona en la mesa con comida, sosteniendo una tableta." }, caption: { en: "Taking it with food helps protect your stomach.", es: "Tomarlo con comida ayuda a proteger su estómago." } },
      { image: IMG + "c92da8850_generated_image.png", alt: { en: "A hand pausing between two pill bottles.", es: "Una mano dudando entre dos frascos de pastillas." }, caption: { en: "Doubling up, or adding other pain relievers like ibuprofen, raises the risk of stomach bleeding.", es: "Tomar el doble, o añadir otros analgésicos como ibuprofeno, aumenta el riesgo de sangrado en el estómago." } },
      { image: IMG + "638ea9dbf_generated_image.png", alt: { en: "A person calmly making a phone call.", es: "Una persona haciendo una llamada con calma." }, caption: { en: "Act right away for black or bloody stools, vomiting blood, chest pain, shortness of breath, weakness on one side or slurred speech.", es: "Actúe de inmediato si hay heces negras o con sangre, vómito con sangre, dolor de pecho, falta de aire, debilidad en un lado o dificultad para hablar." } },
      { image: IMG + "e728bd72f_generated_image.png", alt: { en: "A patient and a clinician talking at a table.", es: "Un paciente y un profesional de salud conversando." }, caption: { en: "Ask your care team before stopping or changing it.", es: "Pregunte a su equipo de atención antes de dejarlo o cambiarlo." } },
    ],
  },
  "eye-drops": {
    medicine: "Prednisolone eye drops",
    source: "Clinician-reviewed fact sheet (sign-off pending)",
    cards: [
      { caption: { en: "After a transplant, your eye needs the drops to calm inflammation.", es: "Después de un trasplante, su ojo necesita las gotas para calmar la inflamación." } },
      { caption: { en: "Missed doses let inflammation build.", es: "Las dosis olvidadas dejan que la inflamación aumente." } },
      { caption: { en: "That can risk rejection of the new tissue, and your vision.", es: "Eso puede poner en riesgo el tejido nuevo y su visión." } },
      { caption: { en: "Talk to your care team before changing anything.", es: "Hable con su equipo de atención antes de cambiar algo." } },
    ],
  },
  antibiotic: {
    medicine: "Amoxicillin",
    source: "Clinician-reviewed fact sheet (sign-off pending)",
    cards: [
      { caption: { en: "The medicine keeps working through the whole course.", es: "El medicamento sigue actuando durante todo el tratamiento." } },
      { caption: { en: "Stopping early or skipping can let the infection come back.", es: "Dejarlo antes o saltarse dosis puede hacer que la infección regrese." } },
      { caption: { en: "Take it as prescribed and ask before stopping.", es: "Tómelo como se lo recetaron y pregunte antes de dejarlo." } },
    ],
  },
};