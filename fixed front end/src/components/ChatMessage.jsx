import { BookOpen, ExternalLink, FileText, Globe, HelpCircle, Image as ImageIcon, Loader2, Mail, Phone, Volume2 } from "lucide-react";
import MessageVisual from "@/components/MessageVisual";
import QuoteCard from "@/components/QuoteCard";
import { useLang } from "@/components/LanguageProvider";
import { speak } from "@/lib/loc";

const TAGS = {
  documents: { icon: FileText, en: "From your documents", es: "De sus documentos" },
  general: { icon: BookOpen, en: "General drug information", es: "Información general del medicamento" },
  unclear: { icon: HelpCircle, en: "This part is unclear", es: "Esta parte no está clara" },
  web: { icon: Globe, en: "From the web: AI summary, check the sources", es: "De internet: resumen con IA, revise las fuentes" },
};

export default function ChatMessage({ message, onEmail, onCall, onVisual }) {
  const { lang, t } = useLang();
  if (message.role === "user") {
    return <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm border border-clinical bg-card px-4 py-3">{message.text}</p>;
  }
  const tag = TAGS[message.tag];
  const Icon = tag.icon;
  return (
    <div className="max-w-[92%] rounded-2xl rounded-bl-sm bg-clinical-50 p-4">
      <p className="flex items-center gap-1.5 text-sm font-semibold text-clinical">
        <Icon className="h-4 w-4" aria-hidden="true" />
        {tag[lang]}
      </p>
      <p className="mt-2">{message.text}</p>
      {message.source && <p className="mt-2 text-sm text-stone">{t("Source", "Fuente")}: {message.source}</p>}
      {message.sources?.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label={t("Sources", "Fuentes")}>
          {message.sources.map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-9 items-center gap-1.5 rounded-full border border-clinical bg-card px-3 py-1 text-sm font-medium text-clinical underline-offset-2 hover:underline">
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                {s.title.length > 48 ? `${s.title.slice(0, 46)}…` : s.title}
              </a>
            </li>
          ))}
        </ul>
      )}
      {message.finding && (
        <div className="mt-3 space-y-2 rounded-xl bg-caution-soft p-3">
          {message.finding.quotes.map((q, i) => <QuoteCard key={i} evidence={q} />)}
        </div>
      )}
      {message.quotes?.length > 0 && (
        <div className="mt-3 space-y-2">
          {message.quotes.map((q, i) => <QuoteCard key={i} evidence={q} />)}
        </div>
      )}
      {message.general && (
        <p className="mt-3 border-l-2 border-clinical pl-3 text-base">
          <span className="font-semibold">{TAGS.general[lang]}: </span>
          {message.general.text} <span className="text-sm text-stone">({message.general.source})</span>
        </p>
      )}
      <MessageVisual visual={message.visual} />
      <div className="mt-3 flex flex-wrap gap-2">
        {message.offerEmail && (
          <button type="button" onClick={() => onEmail(message.finding || null)} className="inline-flex h-11 items-center gap-2 rounded-full border border-foreground bg-card px-4 text-sm font-semibold">
            <Mail className="h-4 w-4" aria-hidden="true" />
            {t("Email my doctor", "Escribir a mi médico")}
          </button>
        )}
        {message.offerEmail && (
          <button type="button" onClick={() => onCall(message.finding || null)} className="inline-flex h-11 items-center gap-2 rounded-full border border-foreground bg-card px-4 text-sm font-semibold">
            <Phone className="h-4 w-4" aria-hidden="true" />
            {t("Call my doctor", "Llamar a mi médico")}
          </button>
        )}
        {message.tag !== "unclear" && !message.visual?.url && (
          <button type="button" onClick={onVisual} disabled={message.visual?.loading} className="inline-flex h-11 items-center gap-2 rounded-full border border-foreground bg-card px-4 text-sm font-semibold disabled:border-border disabled:text-stone">
            {message.visual?.loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <ImageIcon className="h-4 w-4" aria-hidden="true" />}
            {message.visual?.loading ? t("Drawing…", "Dibujando…") : t("See a visual", "Ver una imagen")}
          </button>
        )}
        <button type="button" onClick={() => speak(message.text, lang)} className="inline-flex h-11 items-center gap-2 rounded-full px-3 text-sm font-medium text-clinical">
          <Volume2 className="h-4 w-4" aria-hidden="true" />
          {t("Listen", "Escuchar")}
        </button>
      </div>
    </div>
  );
}