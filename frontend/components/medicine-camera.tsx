'use client';
import { useEffect, useRef, useState } from 'react';
import { Camera, Check, Square } from 'lucide-react';
import { connected, request } from '@/lib/api';
import type { CarePlan, Evidence, PhotoResult } from '@/lib/types';
import { Button } from './ui/button';
import { ReadAloud, Sources } from './patient-ui';

type Identification = PhotoResult & { found: boolean; medication_name: string | null; strength_seen: string | null; confirm_prompt: string; strength_mismatch: boolean; documented_strengths: string[]; citations: Evidence[]; matched_instruction_id: string | null };
export function MedicineCamera({ plan, profileId, spanish }: { plan: CarePlan | null; profileId: string; spanish: boolean }) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const active = useRef(false);
  const generation = useRef(0);
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Identification | null>(null);
  const [intro, setIntro] = useState('');
  const [lastRead, setLastRead] = useState<Identification | null>(null);
  const [introCitations, setIntroCitations] = useState<Evidence[]>([]);
  const t = (en: string, es: string) => spanish ? es : en;
  function stop() { generation.current++; active.current = false; stream.current?.getTracks().forEach(track => track.stop()); stream.current = null; setOn(false); setBusy(false); }
  useEffect(() => () => { generation.current++; active.current = false; stream.current?.getTracks().forEach(track => track.stop()); }, []);
  useEffect(() => { setResult(null); setIntro(''); setIntroCitations([]); }, [plan?.case_id]);
  async function start() {
    setError(''); setResult(null); setIntro('');
    if (!connected) { setError(t('Connect the backend to read a camera image. You can upload or type instead.', 'Conecta el backend para leer la cámara. Puedes subir una foto o escribir.')); return; }
    const token = ++generation.current;
    try {
      const media = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1600 }, height: { ideal: 1200 } }, audio: false });
      if (token !== generation.current) { media.getTracks().forEach(track => track.stop()); return; }
      stream.current = media; active.current = true; setOn(true);
      if (video.current) { video.current.srcObject = media; await video.current.play(); }
    } catch { stop(); setError(t('Camera unavailable or permission denied. Upload a photo or type the label instead.', 'Cámara no disponible o permiso denegado. Sube una foto o escribe la etiqueta.')); }
  }
  async function capture() {
    if (!video.current || !active.current || busy) return;
    const token = generation.current;
    setBusy(true); setError(''); setIntro(''); setResult(null);
    let previous = '';
    try {
      // Two consecutive reads must agree before offering confirmation. Never announce from one frame.
      for (let attempt = 0; attempt < 3; attempt++) {
        if (!active.current || token !== generation.current) return;
        const element = video.current;
        if (!element.videoWidth) throw new Error(t('The camera is not ready. Try again.', 'La cámara aún no está lista. Intenta de nuevo.'));
        const canvas = document.createElement('canvas');
        canvas.width = element.videoWidth; canvas.height = element.videoHeight;
        canvas.getContext('2d')!.drawImage(element, 0, 0);
        const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Capture failed.')), 'image/jpeg', .9));
        const form = new FormData(); form.append('image', blob, 'frame.jpg'); form.append('language', spanish ? 'es' : 'en'); form.append('profile_id', profileId); if (plan) form.append('case_id', plan.case_id);
        const reading = await request<Identification>('/medicine/identify', 'POST', form);
        if (!active.current || token !== generation.current) return;
        setLastRead(reading);
        const key = reading.found && reading.strength_seen ? `${reading.medication_name}:${reading.strength_seen}` : '';
        if (key && key === previous) { setResult(reading); stop(); return; }
        previous = key;
      }
      setError(t('The frames did not agree on a name and strength. Move closer, reduce glare, or use the photo-review reader below.', 'Las lecturas no coincidieron en nombre y concentración. Acerca la etiqueta, reduce el brillo o usa la revisión de fotos.'));
    } catch (cause) { if (token === generation.current) setError(cause instanceof Error ? cause.message : 'Could not read the label.'); }
    finally { if (token === generation.current) setBusy(false); }
  }
  return <section className="panel medicine-camera"><div className="panel-heading"><span className="small-icon"><Camera size={22} /></span><div><h3>{t('Show me your medicine', 'Muéstrame tu medicamento')}</h3><p>{t('Meloxicam / Mobic label reader · confirm before learning more', 'Lector de etiquetas meloxicam / Mobic · confirma antes de continuar')}</p></div></div><p className="helper">{t('Read printed labels only. Keep the name and strength facing the camera. Two frame readings must agree; contents are never identified by pill shape, bottle color, or cap.', 'Solo etiquetas impresas. Orienta el nombre y concentración hacia la cámara. Dos lecturas deben coincidir; no se identifica el contenido por forma o color.')}</p><div hidden={!on} className={`camera-viewport${busy ? ' is-reading' : ''}`}><video ref={video} playsInline muted className="camera-video" aria-label={t('Live bottle camera', 'Cámara del frasco')} /><div className="bottle-guide" aria-hidden="true"><svg viewBox="0 0 260 380" fill="none"><path className="bottle-guide-outline" d="M91 25H169Q178 25 178 34V64H169V83Q169 95 187 107Q208 121 208 145V329Q208 348 189 348H71Q52 348 52 329V145Q52 121 73 107Q91 95 91 83V64H82V34Q82 25 91 25Z" /><path className="bottle-guide-cap" d="M83 64H177M99 36V53M114 36V53M130 36V53M146 36V53M161 36V53" /><rect className="bottle-guide-label" x="66" y="153" width="128" height="104" rx="8" /><path className="bottle-guide-corners" d="M36 141V120H57M203 120H224V141M36 317V339H57M203 339H224V317" /><path className="bottle-guide-scan" d="M66 200H194" /></svg></div><span className="bottle-guide-hint">{busy ? t('Reading · hold steady', 'Leyendo · mantén estable') : t('Center the bottle · label facing forward', 'Centra el frasco · etiqueta hacia la cámara')}</span></div>{on && <p role="status">● {t('Camera on. Frame the label steadily.', 'Cámara encendida. Mantén la etiqueta estable.')}</p>}<div className="form-actions">{!on ? <Button onClick={start} disabled={busy}><Camera size={17} />{t('Turn on camera', 'Encender cámara')}</Button> : <><Button disabled={busy} onClick={capture}>{busy ? t('Checking consecutive frames…', 'Comprobando lecturas…') : t('Read this label', 'Leer esta etiqueta')}</Button><Button variant="secondary" onClick={stop}><Square size={16} />{t('Stop camera', 'Detener cámara')}</Button></>}</div>{error && <p role="alert" className="error-banner">{error}</p>}{lastRead && !result && !busy && <details><summary>{t('Inspect last OCR reading', 'Ver última lectura OCR')}</summary><pre>{JSON.stringify({ found: lastRead.found, strength: lastRead.strength_seen, text: lastRead.text, candidates: lastRead.fields?.map(field => ({field: field.field, value: field.value})) }, null, 2)}</pre></details>}{result && <div className="result-panel"><h3>{result.confirm_prompt}</h3>{result.strength_mismatch && <div className="notice notice-warning">{t('Strength difference: bottle', 'Diferencia de concentración: frasco')} {result.strength_seen} · {t('documents', 'documentos')}: {result.documented_strengths.join(', ')}. {t('Ask your care team to clarify; do not change treatment from this reading.', 'Pide aclaración al equipo; no cambies el tratamiento por esta lectura.')}</div>}{!result.matched_instruction_id && <p>{t('This medicine was not matched to the loaded visit documents.', 'Este medicamento no coincide con los documentos cargados.')}</p>}{!intro && <div className="form-actions"><Button disabled={busy} onClick={async () => { setBusy(true); try { const response = await request<{ mode: string; spoken_text: string; citations: Evidence[] }>('/medicine/intro', 'POST', { medication_name: result.medication_name, confirmed: true, case_id: plan?.case_id, profile_id: profileId, language: spanish ? 'es' : 'en' }); setIntro(response.spoken_text); setIntroCitations(response.citations); } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not load documents.'); } finally { setBusy(false); } }}><Check size={16} />{t('Yes, show my document instructions', 'Sí, mostrar mis instrucciones')}</Button><Button variant="secondary" onClick={() => { setResult(null); setIntro(''); }}>{t('No, try again', 'No, intentar de nuevo')}</Button></div>}{intro && <><p>{intro}</p>{plan && <Sources citations={introCitations} plan={plan} />}<ReadAloud text={intro} language={spanish ? 'es' : 'en'} /><p className="helper">{t('General medicine facts are awaiting human review. This introduction only reads your document evidence.', 'La información general espera revisión humana. Esta introducción solo lee las fuentes de tus documentos.')}</p></>}</div>}</section>;
}
