import { Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import { useLang } from "@/components/LanguageProvider";
import { SAMPLE_CASES } from "@/lib/sampleCases";

export default function SampleVisits() {
  const { lang, t } = useLang();
  return (
    <section id="samples" className="mx-auto max-w-6xl scroll-mt-16 px-4 pb-16 pt-4 sm:px-6 sm:pb-24">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <h2 className="font-display text-4xl font-normal leading-[1.1] tracking-tight">{t("My visits", "Mis visitas")}</h2>
        <p className="max-w-sm text-muted-foreground">
          {t("Sample visits. Each pair of documents shows a different kind of mismatch.", "Visitas de ejemplo. Cada par de documentos muestra un tipo distinto de diferencia.")}
        </p>
      </div>
      <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {SAMPLE_CASES.map((c) => (
          <Link
            key={c.id}
            to="/case/$caseId"
            params={{ caseId: c.id }}
            className={
              c.featured
                ? "group flex flex-col justify-between rounded-2xl bg-foreground p-7 text-background transition-transform duration-200 hover:-translate-y-1 md:col-span-2 lg:col-span-4 lg:flex-row lg:items-end"
                : "group flex min-h-56 flex-col justify-between rounded-2xl border border-border bg-card p-6 transition-all duration-200 hover:-translate-y-1 hover:border-foreground"
            }
          >
            <div>
              <span className={c.featured ? "inline-block rounded-full bg-primary px-3 py-1 text-sm font-semibold text-primary-foreground" : "inline-block rounded-full bg-blush px-3 py-1 text-sm font-medium text-clay"}>
                {c.tag[lang]}
              </span>
              <h3 className={c.featured ? "mt-5 font-display text-4xl leading-[1.1] sm:text-5xl" : "mt-5 text-xl font-semibold"}>{c.title[lang]}</h3>
              <p className={c.featured ? "mt-3 max-w-md text-background/75" : "mt-2 text-muted-foreground"}>{c.blurb[lang]}</p>
            </div>
            <span className="mt-6 inline-flex items-center gap-1.5 text-base font-semibold">
              {t("Open", "Abrir")}
              <ArrowUpRight className="h-5 w-5 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden="true" />
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}