import { AlertTriangle, Sparkles } from "lucide-react";
import QuoteCard from "@/components/QuoteCard";
import { useLang } from "@/components/LanguageProvider";
import { loc } from "@/lib/loc";

function Field({ label, value }) {
  const { lang, t } = useLang();
  return (
    <div className="flex justify-between gap-4 border-t border-border py-2 text-base">
      <dt className="text-stone">{label}</dt>
      <dd className={value ? "text-right font-medium" : "text-right italic text-stone"}>
        {loc(value, lang) || t("Not in your documents", "No está en sus documentos")}
      </dd>
    </div>
  );
}

export default function KeyItemCard({ item, group, disputed, onWhy }) {
  const { lang, t } = useLang();
  const Icon = group.icon;
  return (
    <article className="rounded-2xl border border-border bg-card p-5 sm:p-6">
      <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.14em] text-stone">
        <Icon className="h-4 w-4" aria-hidden="true" />
        {group.title[lang]}
      </p>
      <h3 className="mt-3 text-xl font-semibold leading-snug">{loc(item.name, lang)}</h3>
      {disputed && (
        <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-caution">
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          {t("Your documents disagree on this", "Sus documentos no coinciden en esto")}
        </p>
      )}
      {item.detail && <p className="mt-2 text-stone">{item.detail[lang]}</p>}
      {item.kind === "medication" ? (
        <dl className="mt-3">
          <Field label={t("Amount", "Cantidad")} value={item.amount} />
          <Field label={t("How often", "Frecuencia")} value={item.frequency} />
          <Field label={t("How long", "Duración")} value={item.duration} />
        </dl>
      ) : (
        item.amount && <p className="mt-1 font-medium">{loc(item.amount, lang)}</p>
      )}
      <div className="mt-3"><QuoteCard evidence={item.evidence} /></div>
      {onWhy && (
        <button type="button" onClick={onWhy} className="mt-3 inline-flex h-11 items-center gap-2 rounded-full border border-foreground px-5 text-base font-semibold transition-colors duration-200 hover:bg-foreground hover:text-background">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          {t("Why it matters", "Por qué importa")}
        </button>
      )}
    </article>
  );
}