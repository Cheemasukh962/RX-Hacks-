import { createFileRoute } from "@tanstack/react-router";
import Header from "@/components/Header";
import UploadSection from "@/components/UploadSection";
import { useLang } from "@/components/LanguageProvider";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Patient dashboard | REXO" },
      { name: "description", content: "Upload your visit documents to get started." },
    ],
  }),
  component: DashboardPage,
});

function DashboardPage() {
  const { t } = useLang();
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="border-b border-border bg-muted">
        <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-stone">{t("Patient dashboard", "Panel del paciente")}</p>
          <h1 className="mt-3 font-display text-4xl font-normal leading-[1.1] tracking-tight sm:text-5xl">{t("First, add your documents", "Primero, añada sus documentos")}</h1>
        </div>
      </div>
      <UploadSection />
    </div>
  );
}