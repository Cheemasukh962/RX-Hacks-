// Picks the right language from a { en, es } value; plain strings pass through.
export const loc = (value, lang) => (value && typeof value === "object" ? value[lang] : value);

export const speak = (text, lang) => {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang === "es" ? "es-US" : "en-US";
  window.speechSynthesis.speak(utterance);
};