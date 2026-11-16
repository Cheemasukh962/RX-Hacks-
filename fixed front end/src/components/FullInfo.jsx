import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import ChatBox from "@/components/ChatBox";
import DifferenceCard from "@/components/DifferenceCard";
import KeyItemCard from "@/components/KeyItemCard";
import { GROUPS } from "@/components/KeyItems";
import { useLang } from "@/components/LanguageProvider";

export default function FullInfo({ open, onOpenChange, findings, chat }) {
  const { data, altered, onEmail, onCall } = chat;
  const { lang, t } = useLang();
  const heading = "text-sm font-semibold uppercase tracking-[0.14em] text-stone";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[100dvh] max-w-none flex-col gap-0 p-0 sm:h-[90vh] sm:max-w-6xl sm:rounded-2xl">
        <DialogHeader className="border-b border-border p-5 pr-12 text-left">
          <DialogTitle className="font-display text-3xl font-normal">{t("Full info", "Información completa")}</DialogTitle>
          <DialogDescription>
            {t("Everything REXO found in your documents for this visit. Ask a question about any of it.", "Todo lo que REXO encontró en sus documentos de esta visita. Pregunte sobre cualquier punto.")}
          </DialogDescription>
        </DialogHeader>
        <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,2fr)_minmax(0,3fr)] lg:grid-cols-[minmax(0,1fr)_26rem] lg:grid-rows-1">
          <div className="space-y-8 overflow-y-auto p-5">
            <section>
              <h3 className={heading}>{data.title[lang]}</h3>
              <ul className="mt-3 grid gap-2 text-lg">
                {data.summary[lang].map((line) => (
                  <li key={line} className="flex gap-3">
                    <span className="mt-2.5 h-2 w-2 shrink-0 rounded-full bg-primary" aria-hidden="true" />
                    {line}
                  </li>
                ))}
              </ul>
            </section>
            {GROUPS.map((group) => {
              const items = data.instructions.filter((i) => group.kinds.includes(i.kind));
              return items.length ? (
                <section key={group.id}>
                  <h3 className={heading}>{group.title[lang]}</h3>
                  <div className="mt-3 space-y-4">
                    {items.map((item) => <KeyItemCard key={item.id} item={item} group={group} disputed={item.disputed || (altered && item.disputedWhenAltered)} />)}
                  </div>
                </section>
              ) : null;
            })}
            {findings.length > 0 && (
              <section>
                <h3 className={heading}>{t("Differences flagged", "Diferencias señaladas")}</h3>
                <div className="mt-3 space-y-4">
                  {findings.map((f) => <DifferenceCard key={f.id} finding={f} onEmail={onEmail} onCall={onCall} />)}
                </div>
              </section>
            )}
          </div>
          <div className="flex min-h-0 flex-col border-t border-border bg-muted lg:border-l lg:border-t-0">
            <p className="border-b border-border px-5 py-3 text-sm text-stone">
              {t("Ask about your plan. Demo mode: answers are scripted from sample sources.", "Pregunte sobre su plan. Modo demo: las respuestas vienen de fuentes de ejemplo.")}
            </p>
            <ChatBox {...chat} />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}