import { mockRequest } from './mock';
import { validatePlan } from './safety';
import type { AskResult, BarrierResult, BriefingResult, CarePlan, CaseInput, Context, DemoCase, EvalResult, ExplainResult, FeedbackInput, Mode, PatientProfile, PhotoResult, Style, TeachbackResult } from './types';

const configured = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, '') ?? '';
const baseUrl = configured.endsWith('/api') ? configured : `${configured}/api`;
export const connected = Boolean(configured);
export class ApiError extends Error { constructor(message: string, public status: number) { super(message); this.name = 'ApiError'; } }
export async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  if (!connected) return mockRequest(path, method, body) as Promise<T>;
  const multipart = body instanceof FormData;
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, { method, headers: multipart ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : multipart ? body : JSON.stringify(body), signal: AbortSignal.timeout(30000) });
  } catch { throw new Error('The care service could not be reached. Check the connection and try again. Your text is still here.'); }
  if (!response.ok) {
    // FastAPI errors carry a patient-readable `detail` (e.g. "Voice input is not configured. Please type your answer instead.").
    const detail = await response.json().then((body: { detail?: unknown }) => (typeof body?.detail === 'string' ? body.detail : ''), () => '');
    throw new ApiError(detail || `The care service could not complete this request (${response.status}). Please try again.`, response.status);
  }
  const result = await response.json();
  if (!Array.isArray(result) && result.mode !== 'live' && result.mode !== 'demo') throw new Error('The care service response is missing its live/demo mode.');
  return result as T;
}

// ---- Backend <-> UI shape adapters (only applied when connected to FastAPI) ----
// The backend stores concerns as {id, text, labels, confirmed}; the UI edits plain strings.
type BackendConcern = { id: string; text: string; labels: string[]; confirmed: boolean };
const knownConcerns = new Map<string, BackendConcern>();
type BackendProfile = Omit<PatientProfile, 'concerns' | 'context_opt_in'> & { concerns: (string | BackendConcern)[]; context_opt_in: string | null };
function profileIn(raw: BackendProfile): PatientProfile {
  const concerns = (raw.concerns ?? []).map(item => {
    if (typeof item === 'string') return item;
    knownConcerns.set(item.text, item);
    return item.text;
  });
  return { ...raw, context_opt_in: raw.context_opt_in ?? '', concerns };
}
function profileOut(input: Partial<PatientProfile>): Record<string, unknown> {
  if (!connected || !input.concerns) return input;
  const concerns = input.concerns.map((text, index) => knownConcerns.get(text) ?? { id: `ui-${Date.now()}-${index}`, text, labels: [], confirmed: false });
  return { ...input, concerns };
}
const profileReq = async (path: string, method: string, body?: unknown) => {
  const result = await request<PatientProfile>(path, method, body);
  return connected ? profileIn(result as unknown as BackendProfile) : result;
};
// Backend slot values are strings; the UI renders true / false / null / 'documents_disagree'.
function teachbackIn(result: TeachbackResult): TeachbackResult {
  if (!connected) return result;
  const map = (value: unknown) => value === 'correct' ? true : value === 'incorrect' ? false : value === 'documents_disagree' ? 'documents_disagree' as const : value === true || value === false ? value : null;
  const slot = result.slot_check as Record<string, unknown>;
  return { ...result, slot_check: { dose: map(slot.dose), frequency: map(slot.frequency), duration: map(slot.duration) } };
}

export const api = {
  demoCases: () => request<DemoCase[]>('/demo-cases'),
  createCase: async (input: CaseInput) => validatePlan(await request<CarePlan>('/cases', 'POST', input)),
  getCase: async (id: string) => validatePlan(await request<CarePlan>(`/cases/${encodeURIComponent(id)}`)),
  createProfile: (input: Partial<PatientProfile>) => profileReq('/profile', 'POST', profileOut(input)),
  getProfile: (id: string) => profileReq(`/profile/${encodeURIComponent(id)}`, 'GET'),
  updateProfile: (id: string, input: Partial<PatientProfile>) => profileReq(`/profile/${encodeURIComponent(id)}`, 'PUT', profileOut(input)),
  resetProfile: (id: string) => profileReq(`/profile/${encodeURIComponent(id)}/reset`, 'POST'),
  explain: (input: Context & { instruction_id: string; style_override?: Style }) => request<ExplainResult>('/explain', 'POST', input),
  ask: (input: Context & { question: string }) => request<AskResult>('/ask', 'POST', input),
  teachback: async (input: Context & { instruction_id: string; response_text: string }) => teachbackIn(await request<TeachbackResult>('/teachback', 'POST', input)),
  barrier: (input: Context & { text: string }) => request<BarrierResult>('/barrier', 'POST', input),
  feedback: async (input: FeedbackInput) => {
    const result = await request<{ mode: Mode; profile: PatientProfile; model_updated: boolean }>('/feedback', 'POST', input);
    return connected ? { ...result, profile: profileIn(result.profile as unknown as BackendProfile) } : result;
  },
  briefing: (input: Context & { include: { concerns: string[]; conflicts: string[] } }) => request<BriefingResult>('/briefing', 'POST', input),
  evaluation: () => request<EvalResult>('/eval'),
  reset: () => request<{ mode: Mode; ok: boolean }>('/demo/reset', 'POST'),
  transcribe: (audio: Blob, language: string) => { const form = new FormData(); form.append('audio', audio, 'recording.webm'); form.append('language', language); return request<{ mode: Mode; text: string; language: string }>('/voice/transcribe', 'POST', form); },
  photo: (file: File) => { const form = new FormData(); form.append('image', file); return request<PhotoResult>('/ingest/photo', 'POST', form); },
};
