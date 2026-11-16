import { useEffect, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowUpRight, Loader2 } from "lucide-react";
import { useLang } from "@/components/LanguageProvider";
import { api, savedVisits } from "@/api/rexo";

const cardClass = "group flex min-h-48 flex-col justify-between rounded-2xl border border-border bg-card p-6 text-left transition-all duration-200 hover:-translate-y-1 hover:border-foreground";

// Visits from the connected REXO backend: the patient's uploads (this device) and the backend's samples.
export default function LiveVisits() {
  const { t } = useLang();
  const navigate = useNavigate();
  const [mine, setMine] = useState([]);
  const [samples, setSamples] = useState(null);
  const [opening, setOpening] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setMine(savedVisits());
    api.demoCases().then(setSamples).catch((e) => { setSamples([]); setError(e.message); });
  }, []);

  const openSample = async (id) => {
    setOpening(id);
    setError("");
    try {
      const plan = await api.createDemoCase(id);
      navigate({ to: "/case/$caseId", params: { caseId: plan.case_id } });
    } catch (e) {
      setError(e.message);
      setOpening("");
    }
  };

  return (
    <section className="mx-auto max-w-6xl px-4 pb-6 pt-4 sm:px-6">
      {error && <p role="alert" className="mb-6 rounded-xl bg-caution-soft px-4 py-3">{error}</p>}
      {mine.length > 0 && (
        <>
          <h2 className="font-display text-4xl font-normal leading-[1.1] tracking-tight">{t("Your visits", "Sus visitas")}</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {mine.map((v) => (
              <Link key={v.id} to="/case/$caseId" params={{ caseId: v.id }} className={cardClass}>
                <div>
                  <span className="inline-block rounded-full bg-primary px-3 py-1 text-sm font-semibold text-primary-foreground">{t("Uploaded", "Subida")}</span>
                  <h3 className="mt-4 text-xl font-semibold">{v.title}</h3>
                  <p className="mt-1 text-muted-foreground">{new Date(v.at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}</p>
                </div>
                <span className="mt-4 inline-flex items-center gap-1.5 font-semibold">{t("Open", "Abrir")}<ArrowUpRight className="h-5 w-5" aria-hidden="true" /></span>
              </Link>
            ))}
          </div>
        </>
      )}
      <h2 className="mt-12 font-display text-4xl font-normal leading-[1.1] tracking-tight">{t("Sample visits", "Visitas de ejemplo")}</h2>
      <p className="mt-2 text-muted-foreground">{t("Fictional records read by the live REXO service.", "Registros ficticios leídos por el servicio REXO.")}</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {samples === null && <Loader2 className="h-6 w-6 animate-spin text-stone" aria-label={t("Loading", "Cargando")} />}
        {samples?.map((c) => (
          <button key={c.case_id} type="button" onClick={() => openSample(c.case_id)} disabled={!!opening} className={cardClass}>
            <div>
              <span className="inline-block rounded-full bg-blush px-3 py-1 text-sm font-medium text-clay">{t("Synthetic", "Sintético")}</span>
              <h3 className="mt-4 text-xl font-semibold">{c.title}</h3>
              <p className="mt-1 text-muted-foreground">{c.description}</p>
            </div>
            <span className="mt-4 inline-flex items-center gap-1.5 font-semibold">
              {opening === c.case_id ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <ArrowUpRight className="h-5 w-5" aria-hidden="true" />}
              {t("Open", "Abrir")}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
