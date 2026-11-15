import { mockRequest } from './mock';
import { validatePlan } from './safety';
import type { AskResult, BarrierResult, BriefingResult, CarePlan, CaseInput, Context, DemoCase, EvalResult, ExplainResult, FeedbackInput, Mode, PatientProfile, PhotoResult, Style, TeachbackResult } from './types';

const configured = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, '') ?? '';
const baseUrl = configured.endsWith('/api') ? configured : `${configured}/api`;
export const connected = Boolean(configured);
export async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  if (!connected) return mockRequest(path, method, body) as Promise<T>;
  const multipart = body instanceof FormData;
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, { method, headers: multipart ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : multipart ? body : JSON.stringify(body), signal: AbortSignal.timeout(30000) });
  } catch { throw new Error('The care service could not be reached. Check the connection and try again. Your text is still here.'); }
  if (!response.ok) throw new Error(`The care service could not complete this request (${response.status}). Please try again.`);
  const result = await response.json();
  if (!Array.isArray(result) && result.mode !== 'live' && result.mode !== 'demo') throw new Error('The care service response is missing its live/demo mode.');
  return result as T;
}
export const api = {
  demoCases: () => request<DemoCase[]>('/demo-cases'),
  createCase: async (input: CaseInput) => validatePlan(await request<CarePlan>('/cases', 'POST', input)),
  getCase: async (id: string) => validatePlan(await request<CarePlan>(`/cases/${encodeURIComponent(id)}`)),
  createProfile: (input: Partial<PatientProfile>) => request<PatientProfile>('/profile', 'POST', input),
  getProfile: (id: string) => request<PatientProfile>(`/profile/${encodeURIComponent(id)}`),
  updateProfile: (id: string, input: Partial<PatientProfile>) => request<PatientProfile>(`/profile/${encodeURIComponent(id)}`, 'PUT', input),
  resetProfile: (id: string) => request<PatientProfile>(`/profile/${encodeURIComponent(id)}/reset`, 'POST'),
  explain: (input: Context & { instruction_id: string; style_override?: Style }) => request<ExplainResult>('/explain', 'POST', input),
  ask: (input: Context & { question: string }) => request<AskResult>('/ask', 'POST', input),
  teachback: (input: Context & { instruction_id: string; response_text: string }) => request<TeachbackResult>('/teachback', 'POST', input),
  barrier: (input: Context & { text: string }) => request<BarrierResult>('/barrier', 'POST', input),
  feedback: (input: FeedbackInput) => request<{ mode: Mode; profile: PatientProfile; model_updated: boolean }>('/feedback', 'POST', input),
  briefing: (input: Context & { include: { concerns: string[]; conflicts: string[] } }) => request<BriefingResult>('/briefing', 'POST', input),
  evaluation: () => request<EvalResult>('/eval'),
  reset: () => request<{ mode: Mode; ok: boolean }>('/demo/reset', 'POST'),
  transcribe: (audio: Blob, language: string) => { const form = new FormData(); form.append('audio', audio, 'recording.webm'); form.append('language', language); return request<{ mode: Mode; text: string; language: string }>('/voice/transcribe', 'POST', form); },
  photo: (file: File) => { const form = new FormData(); form.append('image', file); return request<PhotoResult>('/ingest/photo', 'POST', form); },
};
