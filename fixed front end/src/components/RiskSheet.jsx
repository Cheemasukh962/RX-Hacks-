import { Pill } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Image } from "@/components/ui/image";
import { useLang } from "@/components/LanguageProvider";
import { RISK_CARDS } from "@/lib/riskCards";

export default function RiskSheet({ caseId, open, onOpenChange }) {
  const { lang, t } = useLang();
  const set = RISK_CARDS[caseId];
  if (!set) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader className="text-left">
          <DialogTitle className="font-display text-3xl font-normal">{t("Why it matters", "Por qué importa")}</DialogTitle>
          <DialogDescription>{set.medicine} · {t("General drug information", "Información general del medicamento")}</DialogDescription>
        </DialogHeader>
        <ol className="flex snap-x gap-4 overflow-x-auto pb-2 sm:grid sm:grid-cols-2 sm:overflow-visible lg:grid-cols-4">
          {set.cards.map((card, i) => (
            <li key={i} className="w-64 shrink-0 snap-start overflow-hidden rounded-2xl border border-border bg-card sm:w-auto">
              {card.image ? (
                <Image src={card.image} alt={card.alt[lang]} className="aspect-square w-full" />
              ) : (
                <div className="flex aspect-square items-center justify-center bg-blush" aria-hidden="true">
                  <Pill className="h-12 w-12 text-clay" />
                </div>
              )}
              <p className="p-4 text-base font-medium">
                <span className="mr-2 text-stone">{i + 1}.</span>
                {card.caption[lang]}
              </p>
            </li>
          ))}
        </ol>
        <div className="space-y-1 text-sm text-stone">
          <p>{t("Illustration, not a prediction for you.", "Ilustración, no una predicción para usted.")}</p>
          <p className="font-semibold text-foreground">{t("Talk to your care team before stopping or changing any medicine.", "Hable con su equipo de atención antes de dejar o cambiar cualquier medicina.")}</p>
          <p>{t("Source", "Fuente")}: {set.source}</p>
        </div>
      </DialogContent>
    </Dialog>
  );
}