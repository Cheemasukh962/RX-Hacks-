import { useRef, useState } from "react";
import { api, connected } from "@/api/rexo";

// Speech to text. Connected: records with MediaRecorder and transcribes with Deepgram through the
// REXO backend (/api/voice/transcribe; handles English, Spanish and a mix of both).
// Demo mode: the browser's own speech recognition, where available.
export default function useDictation(lang, onText) {
  const [listening, setListening] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const recRef = useRef(null);
  const streamRef = useRef(null);

  const startBrowser = () => {
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

  const startRecorder = async () => {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") return setBlocked(true);
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      return setBlocked(true);
    }
    streamRef.current = stream;
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      setListening(false);
      const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      if (!blob.size) return;
      setBusy(true);
      try {
        // "multi" lets Deepgram follow a patient who mixes Spanish and English.
        const result = await api.transcribe(blob, lang === "es" ? "multi" : "en");
        if (result.text?.trim()) onText(result.text.trim());
      } catch (e) {
        setError(e.message);
      } finally {
        setBusy(false);
      }
    };
    recRef.current = recorder;
    recorder.start();
    setListening(true);
  };

  const start = () => (connected ? startRecorder() : startBrowser());
  const stop = () => {
    const rec = recRef.current;
    // SpeechRecognition has no state; a MediaRecorder must still be recording.
    if (rec && listening && (rec.state === undefined || rec.state === "recording")) rec.stop();
  };

  return { listening, blocked, busy, error, start, stop };
}
