import { FileText } from "lucide-react";
import { useLang } from "@/components/LanguageProvider";
import { DOC_LABELS } from "@/lib/sampleCases";

export default function QuoteCard({ evidence }) {
  const { lang, t } = useLang();
  return (
    <figure className="h-full rounded-xl border border-border bg-card p-4">
      <figcaption className="flex flex-wrap items-center gap-2 text-sm font-semibold text-stone">
        <FileText className="h-4 w-4" aria-hidden="true" />
        {DOC_LABELS[evidence.doc][lang]}
        {evidence.altered && (
          <span className="rounded-full bg-foreground px-2 py-0.5 text-xs font-semibold tracking-wide text-background">DEMO-ALTERED</span>
        )}
      </figcaption>
      <blockquote className="mt-2 font-display text-[17px] italic leading-snug">“{evidence.quote}”</blockquote>
      {lang === "es" && <p className="mt-2 text-sm text-muted-foreground">{t("", "(original, en inglés)")}</p>}
    </figure>
  );
}