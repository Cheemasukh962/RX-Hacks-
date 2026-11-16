import { useState } from "react";
import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { ArrowLeft, BookOpen, Camera, CheckCircle2, Info, MessageCircle } from "lucide-react";
import FullInfo from "@/components/FullInfo";
import Header from "@/components/Header";
import DifferenceCard from "@/components/DifferenceCard";
import KeyItems from "@/components/KeyItems";
import ChatPanel from "@/components/ChatPanel";
import CallDoctor from "@/components/CallDoctor";
import EmailComposer from "@/components/EmailComposer";
import RiskSheet from "@/components/RiskSheet";
import MedicineCamera from "@/components/MedicineCamera";
import { useLang } from "@/components/LanguageProvider";
import { getCase } from "@/lib/sampleCases";
import { RISK_CARDS } from "@/lib/riskCards";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/case/$caseId")({
  loader: ({ params }) => {
    if (!getCase(params.caseId)) throw notFound();
  },
  head: () => ({ meta: [{ title: "Your plan | REXO" }] }),
  component: CasePage,
});

function CasePage() {
  const { caseId } = Route.useParams();
  return <CaseView key={caseId} data={getCase(caseId)} />;
}

function CaseView({ data }) {
  const { lang, t } = useLang();
  const [altered, setAltered] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [email, setEmail] = useState(undefined);
  const [riskOpen, setRiskOpen] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [fullOpen, setFullOpen] = useState(false);
  const [call, setCall] = useState(undefined);
  const [settings, setSettings] = useState({ autoRead: false, largeText: false });
  const findings = data.findings.filter((f) => !f.alteredOnly || altered);
  const onVisual = RISK_CARDS[data.id] ? () => setRiskOpen(true) : null;
  const chat = { data, altered, messages, setMessages, onEmail: setEmail, onCall: setCall, settings, setSettings };

  return (
    <div className="min-h-screen bg-background pb-28">
      <Header />
      <div className="border-b border-border bg-muted">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p className="flex items-center gap-2 text-sm text-stone">
            <Info className="h-4 w-4 shrink-0" aria-hidden="true" />
            {data.synthetic
              ? t("Synthetic demo record, not a real patient", "Registro de demostración sintético, no un paciente real")
              : t("Sample data based on a real visit, used with consent. Identifiers removed.", "Datos de ejemplo de una visita real, usados con permiso. Sin identificadores.")}
          </p>
          {data.hasAltered && (
            <div className="flex rounded-full border border-border bg-card p-0.5" role="group" aria-label={t("Document version", "Versión de los documentos")}>
              {[[false, t("Original documents", "Documentos originales")], [true, t("Demo-altered", "Alterado para demo")]].map(([value, label]) => (
                <button key={label} type="button" aria-pressed={altered === value} onClick={() => setAltered(value)} className={cn("h-10 rounded-full px-4 text-sm font-semibold transition-colors duration-200", altered === value ? "bg-foreground text-background" : "text-stone")}>
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <section className="bg-secondary">
        <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
          <Link to="/visits" className="inline-flex h-11 items-center gap-1.5 text-sm font-semibold text-clinical">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            {t("Back to my visits", "Volver a mis visitas")}
          </Link>
          <p className="mt-4 text-sm font-semibold uppercase tracking-[0.14em] text-stone">{data.title[lang]}</p>
          <h1 className="mt-2 font-display text-5xl font-normal leading-[1.05] tracking-tight sm:text-6xl">{t("Here's your plan", "Este es su plan")}</h1>
          <ul className="mt-8 grid max-w-3xl gap-3 text-lg">
            {data.summary[lang].map((line) => (
              <li key={line} className="flex gap-3">
                <span className="mt-2.5 h-2 w-2 shrink-0 rounded-full bg-primary" aria-hidden="true" />
                {line}
              </li>
            ))}
          </ul>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button type="button" onClick={() => setCameraOpen(true)} className="inline-flex h-12 items-center justify-center gap-2 rounded-full border border-foreground px-6 text-base font-semibold transition-colors duration-200 hover:bg-foreground hover:text-background">
              <Camera className="h-5 w-5" aria-hidden="true" />
              {t("Show me your medicine", "Muéstreme su medicina")}
            </button>
            <button type="button" onClick={() => setFullOpen(true)} className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-foreground px-6 text-base font-semibold text-background transition-colors duration-200 hover:bg-charcoal">
              <BookOpen className="h-5 w-5" aria-hidden="true" />
              {t("Full info", "Información completa")}
            </button>
          </div>
        </div>
      </section>

      <main className="mx-auto max-w-6xl space-y-16 px-4 py-14 sm:px-6">
        <section aria-labelledby="differences">
          <h2 id="differences" className="font-display text-4xl font-normal leading-[1.1]">{t("Differences flagged", "Diferencias señaladas")}</h2>
          {findings.length ? (
            <div className="mt-6 space-y-4">
              {findings.map((f) => <DifferenceCard key={f.id} finding={f} onEmail={setEmail} onCall={setCall} />)}
            </div>
          ) : (
            <p className="mt-6 flex items-center gap-2 rounded-2xl bg-sage-soft p-5 font-semibold text-sage">
              <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
              {t("Your two documents match.", "Sus dos documentos coinciden.")}
            </p>
          )}
        </section>
        <section aria-labelledby="key-items">
          <h2 id="key-items" className="font-display text-4xl font-normal leading-[1.1]">{t("Key items", "Puntos clave")}</h2>
          <div className="mt-6">
            <KeyItems data={data} altered={altered} onWhy={onVisual} />
          </div>
        </section>
      </main>

      <button type="button" onClick={() => setChatOpen(true)} className="fixed inset-x-4 bottom-4 z-30 inline-flex h-14 items-center justify-center gap-2 rounded-full bg-primary px-8 text-base font-semibold text-primary-foreground shadow-lg transition-colors duration-200 hover:bg-signal-600 sm:inset-x-auto sm:right-6">
        <MessageCircle className="h-5 w-5" aria-hidden="true" />
        {t("Let's chat", "Conversemos")}
      </button>

      <ChatPanel open={chatOpen} onOpenChange={setChatOpen} {...chat} />
      <FullInfo open={fullOpen} onOpenChange={setFullOpen} findings={findings} chat={chat} />
      {call !== undefined && <CallDoctor finding={call} onClose={() => setCall(undefined)} />}
      <RiskSheet caseId={data.id} open={riskOpen} onOpenChange={setRiskOpen} />
      {email !== undefined && <EmailComposer finding={email} onClose={() => setEmail(undefined)} />}
      {cameraOpen && (
        <MedicineCamera
          data={data}
          onClose={() => setCameraOpen(false)}
          onConfirmed={(message) => { setMessages((m) => [...m, message]); setCameraOpen(false); setChatOpen(true); }}
        />
      )}
    </div>
  );
}