import { useRef, useState } from "react";

// Browser speech-to-text for demo mode. The live build swaps this for /api/voice/transcribe.
export default function useDictation(lang, onText) {
  const [listening, setListening] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const recRef = useRef(null);

  const start = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return setBlocked(true);
    const rec = new SR();
    rec.lang = lang === "es" ? "es-US" : "en-US";
    rec.interimResults = true;
    rec.onresult = (e) => onText(Array.from(e.results).map((r) => r[0].transcript).join(" "));
    rec.onend = () => setListening(false);
    rec.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") setBlocked(true);
      setListening(false);
    };
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  const stop = () => recRef.current?.stop();

  return { listening, blocked, start, stop };
}