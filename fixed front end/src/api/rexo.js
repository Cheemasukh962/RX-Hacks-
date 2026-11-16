// REXO FastAPI client. Set VITE_REXO_API_URL (e.g. http://localhost:8000) to connect;
// without it the app stays in demo mode on the local sample data.
const RAW = (import.meta.env.VITE_REXO_API_URL || "").trim().replace(/\/+$/, "");
const BASE = RAW ? (RAW.endsWith("/api") ? RAW : `${RAW}/api`) : "";

export const connected = Boolean(BASE);

async function call(path, { method = "GET", json, form, timeout = 120000 } = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers: json ? { "Content-Type": "application/json" } : undefined,
      body: json ? JSON.stringify(json) : form,
      signal: AbortSignal.timeout(timeout),
    });
  } catch {
    throw new Error("The REXO service could not be reached. Check that the backend is running, then try again.");
  }
  if (!response.ok) {
    const detail = await response.json().then((b) => (typeof b?.detail === "string" ? b.detail : ""), () => "");
    const error = new Error(detail || `The REXO service could not complete this request (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

const upload = (field, blob, filename, extra = {}) => {
  const form = new FormData();
  form.append(field, blob, filename);
  Object.entries(extra).forEach(([k, v]) => v !== undefined && v !== null && form.append(k, v));
  return form;
};

export const api = {
  demoCases: () => call("/demo-cases"),
  createDemoCase: (demoCaseId) => call("/cases", { method: "POST", json: { demo_case_id: demoCaseId } }),
  createCase: (documents) => call("/cases", { method: "POST", json: { documents } }),
  getCase: (caseId) => call(`/cases/${encodeURIComponent(caseId)}`),
  insights: (caseId) => call(`/cases/${encodeURIComponent(caseId)}/insights`, { method: "POST", json: {} }),
  demoAltered: (caseId) => call(`/cases/${encodeURIComponent(caseId)}/demo-altered`, { method: "POST" }),
  ingestPdf: (file) => call("/ingest/pdf", { method: "POST", form: upload("file", file, file.name) }),
  chat: ({ caseId, language, level, messages, medication }) =>
    call("/chat", { method: "POST", json: { case_id: caseId, language, level, messages, medication } }),
  transcribe: (blob, language) =>
    call("/voice/transcribe", { method: "POST", form: upload("audio", blob, "recording.webm", { language }) }),
  identifyMedicine: (blob, language, caseId) =>
    call("/medicine/identify", { method: "POST", form: upload("image", blob, "label.jpg", { language, case_id: caseId }) }),
  medicineIntro: ({ medicationName, caseId, language }) =>
    call("/medicine/intro", { method: "POST", json: { medication_name: medicationName, confirmed: true, case_id: caseId, language } }),
  rewriteEmail: ({ body, note, topic, language }) =>
    call("/email/rewrite", { method: "POST", json: { body, note, topic, language } }),
};

// Visits the patient uploaded, kept on this device only (ids + titles, no document text).
const VISITS_KEY = "rexo-visits";
export const savedVisits = () => {
  try { return JSON.parse(localStorage.getItem(VISITS_KEY) || "[]"); } catch { return []; }
};
export const saveVisit = (visit) => {
  try {
    const rest = savedVisits().filter((v) => v.id !== visit.id);
    localStorage.setItem(VISITS_KEY, JSON.stringify([visit, ...rest].slice(0, 10)));
  } catch { /* storage unavailable: the visit still opens */ }
};
