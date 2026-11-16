'use client';

import { useRef, useState } from 'react';
import { Camera, Check, LoaderCircle, Plus, Trash2 } from 'lucide-react';
import { api, connected } from '@/lib/api';
import type { PhotoResult } from '@/lib/types';
import { Button } from './ui/button';

export function BottleScanner({ spanish, onUseText }: { spanish: boolean; onUseText: (text: string) => void }) {
  const [scans, setScans] = useState<PhotoResult[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [review, setReview] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const t = (en: string, es: string) => spanish ? es : en;
  async function scan(file?: File) {
    if (!file) return;
    setError(''); setPending(true); setConfirmed(false);
    try {
      if (file.size > 8 * 1024 * 1024) throw new Error(t('Choose an image under 8 MB.', 'Elige una imagen de menos de 8 MB.'));
      const result = await api.photo(file);
      setScans(previous => [...previous, result]);
      setReview(previous => [previous, result.text].filter(Boolean).join('\n'));
    } catch (cause) { setError(cause instanceof Error ? cause.message : t('Could not read this label. Try a closer photo or type the text.', 'No se pudo leer. Acerca la foto o escribe el texto.')); }
    finally { setPending(false); if (input.current) input.current.value = ''; }
  }
  return <section className="panel bottle-scanner"><div className="panel-heading"><span className="small-icon"><Camera size={21} /></span><div><h3>{t('Read a medicine bottle', 'Leer un frasco de medicamento')}</h3><p>{t('Photograph the printed label. Review every result.', 'Fotografía la etiqueta impresa. Revisa cada resultado.')}</p></div></div>
    <p>{t('Place the bottle in even light, fill the photo with the label, and keep the text facing the camera. Add the back as a separate photo. Covered or curved text cannot be recovered reliably.', 'Usa luz uniforme, llena la foto con la etiqueta y orienta el texto hacia la cámara. Agrega otra foto del reverso. No se puede recuperar texto cubierto o curvado con fiabilidad.')}</p>
    <p className="helper">{t('Local OCR only: photos are processed on the connected server, not sent to an external AI service. Medication-related fragments are returned; review them for personal details. Bottle contents and clinical correctness are not verified.', 'OCR local: las fotos se procesan en el servidor conectado, sin servicios externos de IA. Se devuelven fragmentos del medicamento; revisa que no incluyan datos personales. No se verifica el contenido ni la exactitud clínica.')}</p>
    <input ref={input} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" aria-label={t('Choose bottle-label image', 'Elegir foto de etiqueta')} onChange={event => void scan(event.target.files?.[0])} />
    <div className="form-actions"><Button disabled={pending} variant="secondary" onClick={() => input.current?.click()}>{pending ? <LoaderCircle className="spin" size={17} /> : scans.length ? <Plus size={17} /> : <Camera size={17} />}{pending ? t('Reading label…', 'Leyendo etiqueta…') : scans.length ? t('Add another side', 'Agregar otro lado') : t('Choose bottle photo', 'Elegir foto del frasco')}</Button>{!!scans.length && <Button disabled={pending} variant="ghost" onClick={() => { setScans([]); setReview(''); setConfirmed(false); setError(''); }}><Trash2 size={16} />{t('Clear scans', 'Borrar lecturas')}</Button>}</div>
    {!connected && <p className="helper">{t('Connect the backend to enable OCR. Typing and sample cases remain available.', 'Conecta el backend para activar OCR. Puedes escribir o usar ejemplos.')}</p>}
    {error && <p className="error-banner" role="alert">{error}</p>}
    {scans.map((result, index) => <div className="bottle-result" key={index}><h4>{t('Photo', 'Foto')} {index + 1} · {t('Unverified transcription', 'Transcripción sin verificar')}</h4>{!result.fields?.length && <p className="notice notice-warning">{t('No supported fields found. Retake a closer front-facing photo, or type what you can read.', 'No se encontraron campos. Acerca la foto o escribe lo que puedes leer.')}</p>}{!!result.fields?.length && <div className="table-scroll"><table><thead><tr><th>{t('Label field', 'Campo')}</th><th>{t('Candidate', 'Candidato')}</th><th>{t('Exact OCR fragment', 'Fragmento OCR exacto')}</th></tr></thead><tbody>{result.fields.map((field, i) => <tr key={i}><th scope="row">{field.field.replaceAll('_', ' ')}{result.conflicting_fields?.includes(field.field) && <span className="status-badge warning">{t('Candidates disagree', 'Candidatos distintos')}</span>}</th><td>{field.value}</td><td><q>{field.evidence.quote}</q></td></tr>)}</tbody></table></div>}<ul className="plain-list">{result.warnings?.map((warning, i) => <li key={i}>{warning}</li>)}</ul><details><summary>{t('Medication-only OCR preview', 'Vista previa de OCR del medicamento')}</summary><pre>{result.text || t('No readable medication fragments.', 'Sin fragmentos legibles.')}</pre></details></div>)}
    {!!scans.length && <><label className="field"><span>{t('Review and correct the combined label text', 'Revisa y corrige el texto combinado')}</span><textarea rows={7} value={review} onChange={event => { setReview(event.target.value); setConfirmed(false); }} /><span className="helper">{t('Different candidates from different photos stay visible above. Resolve transcription uncertainty against the bottle; do not choose between conflicting treatment instructions here.', 'Los candidatos distintos se conservan arriba. Verifica el texto con el frasco; no elijas entre instrucciones de tratamiento contradictorias.')}</span></label><label className="checkbox-line"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />{t('I checked every field against a fictional label, removed any personal information, and confirm this text is synthetic demo data.', 'Verifiqué cada campo con una etiqueta ficticia, eliminé los datos personales y confirmo que es texto sintético.')}</label><Button disabled={pending || !confirmed || !review.trim()} onClick={() => onUseText(review)}><Check size={16} />{t('Use reviewed synthetic text', 'Usar texto sintético revisado')}</Button><p className="helper">{t('Real reference labels can be inspected locally; only synthetic text belongs in the demo care-plan flow.', 'Puedes inspeccionar etiquetas reales localmente; solo texto sintético debe entrar al plan demo.')}</p></>}
  </section>;
}
