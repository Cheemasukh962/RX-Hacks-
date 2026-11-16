import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Info } from "lucide-react";
import Header from "@/components/Header";
import SampleVisits from "@/components/SampleVisits";
import { useLang } from "@/components/LanguageProvider";
import { UPLOADED_KEY } from "@/components/UploadSection";

export const Route = createFileRoute("/visits")({
  head: () => ({
    meta: [
      { title: "My visits | REXO" },
      { name: "description", content: "Open a visit to see your plan and any differences between your documents." },
    ],
  }),
  component: VisitsPage,
});

function VisitsPage() {
  const { t } = useLang();
  const navigate = useNavigate();
  const [allowed, setAllowed] = useState(false);

  // Visits come after the upload step: without it, send the patient back to upload.
  useEffect(() => {
    if (localStorage.getItem(UPLOADED_KEY)) setAllowed(true);
    else navigate({ to: "/dashboard", replace: true });
  }, [navigate]);

  if (!allowed) return null;
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="border-b border-border bg-muted">
        <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-stone">{t("Patient dashboard", "Panel del paciente")}</p>
          <h1 className="mt-3 font-display text-4xl font-normal leading-[1.1] tracking-tight sm:text-5xl">{t("Your visits", "Sus visitas")}</h1>
        </div>
      </div>
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div role="status" className="flex items-start gap-3 rounded-2xl bg-clinical-50 p-5">
          <Info className="mt-1 h-5 w-5 shrink-0 text-clinical" aria-hidden="true" />
          <p>{t("Demo mode: the reading service isn't connected here, so your documents were not read or sent anywhere. The visits below are samples.", "Modo demo: el servicio de lectura no está conectado, así que sus documentos no se leyeron ni se enviaron. Las visitas de abajo son ejemplos.")}</p>
        </div>
      </div>
      <SampleVisits />
    </div>
  );
}