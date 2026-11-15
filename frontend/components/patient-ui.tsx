'use client';

import { useEffect, useRef, useState } from 'react';
import { AlertCircle, ArrowUpRight, BookOpen, Check, FileText, Mic, Square, Volume2 } from 'lucide-react';
import { api, connected } from '@/lib/api';
import type { CarePlan, Evidence, Language } from '@/lib/types';
import { verifiedEvidence } from '@/lib/safety';
import { Button } from './ui/button';

export function SourceQuote({ evidence, plan, expanded = false }: { evidence: Evidence; plan: CarePlan; expanded?: boolean }) {
  if (!verifiedEvidence(plan, evidence)) return <p className="error-text">Source quote could not be verified.</p>;
  const document = plan.documents.find(doc => doc.id === evidence.document_id)!;
  return <details className="source" open={expanded || undefined}><summary><FileText size={14} />{document.title}<span>{evidence.document_id}</span><ArrowUpRight size={13} /></summary><blockquote>“{evidence.quote}”</blockquote></details>;
}

export function Sources({ citations, plan }: { citations: Evidence[]; plan: CarePlan }) {
  return <div className="source-list">{citations.map((evidence, index) => <SourceQuote key={`${evidence.document_id}-${index}`} evidence={evidence} plan={plan} expanded />)}</div>;
}

export function EmptyState({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="empty-state"><BookOpen size={28} /><h3>{title}</h3><p>{children}</p></div>;
}

export function VoiceInput({ language, onText, disabled }: { language: Language; onText: (text: string) => void; disabled?: boolean }) {
  const [recording, setRecording] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; if (recorder.current) recorder.current.onstop = null; stream.current?.getTracks().forEach(track => track.stop()); }; }, []);
  async function record() {
    setError('');
    if (recording) { recorder.current?.stop(); setRecording(false); return; }
    if (!connected) { setError(language === 'es' ? 'La voz requiere el backend. Puedes escribir tu respuesta.' : 'Voice needs the connected backend. You can type your response.'); return; }
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') throw new Error('This browser cannot record audio. Please type instead.');
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) { stream.current.getTracks().forEach(track => track.stop()); return; }
      const chunks: Blob[] = [];
      const current = new MediaRecorder(stream.current);
      recorder.current = current;
      current.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      current.onstop = async () => {
        stream.current?.getTracks().forEach(track => track.stop());
        if (!mounted.current) return;
        setPending(true);
        try { const result = await api.transcribe(new Blob(chunks, { type: current.mimeType }), language); if (mounted.current) onText(result.text); }
        catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : 'Transcription failed. Please type instead.'); }
        finally { if (mounted.current) setPending(false); }
      };
      current.start(); setRecording(true);
    } catch { stream.current?.getTracks().forEach(track => track.stop()); setError(language === 'es' ? 'No se pudo usar el micrófono. Puedes escribir.' : 'Microphone unavailable or permission denied. You can type instead.'); }
  }
  return <div className="voice-control"><Button type="button" variant="ghost" onClick={record} disabled={disabled || pending}>{recording ? <Square size={17} /> : <Mic size={17} />}{pending ? language === 'es' ? 'Transcribiendo…' : 'Transcribing…' : recording ? language === 'es' ? 'Terminar grabación' : 'Stop recording' : language === 'es' ? 'Usar mi voz' : 'Use my voice'}</Button>{error && <p role="status" className="helper">{error}</p>}</div>;
}

export function ReadAloud({ text, language }: { text: string; language: Language }) {
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => () => { if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel(); }, [text]);
  function speak() {
    if (!('speechSynthesis' in window)) { setError('Read aloud is unavailable in this browser. The full text is shown here.'); return; }
    speechSynthesis.cancel();
    if (speaking) { setSpeaking(false); return; }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language === 'es' ? 'es-ES' : 'en-US';
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => { setSpeaking(false); setError('Audio playback is unavailable. The full text is shown here.'); };
    setSpeaking(true); speechSynthesis.speak(utterance);
  }
  return <div><Button variant="ghost" onClick={speak}><Volume2 size={17} />{speaking ? language === 'es' ? 'Detener audio' : 'Stop audio' : language === 'es' ? 'Escuchar explicación' : 'Listen to explanation'}</Button>{error && <p role="status">{error}</p>}</div>;
}

export function Notice({ children, tone = 'info' }: { children: React.ReactNode; tone?: 'info' | 'success' | 'warning' }) {
  return <div className={`notice notice-${tone}`}>{tone === 'success' ? <Check size={18} /> : <AlertCircle size={18} />}<div>{children}</div></div>;
}
