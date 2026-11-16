import { Phone, Siren } from "lucide-react";
import { useLang } from "@/components/LanguageProvider";

export default function UrgentPanel({ onResume }) {
  const { t } = useLang();
  return (
    <div role="alert" className="rounded-2xl bg-danger p-6 text-destructive-foreground">
      <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.14em]">
        <Siren className="h-5 w-5" aria-hidden="true" />
        {t("Get help now", "Busque ayuda ahora")}
      </p>
      <p className="mt-3 font-display text-3xl leading-[1.1]">{t("Call 911 or your care team now.", "Llame al 911 o a su equipo de atención ahora.")}</p>
      <p className="mt-3">{t("What you described can be an emergency. The chat is paused.", "Lo que describió puede ser una emergencia. El chat está en pausa.")}</p>
      <a href="tel:911" className="mt-5 inline-flex h-14 w-full items-center justify-center gap-2 rounded-full bg-background text-base font-semibold text-foreground">
        <Phone className="h-5 w-5" aria-hidden="true" />
        {t("Call 911", "Llamar al 911")}
      </a>
      <button type="button" onClick={onResume} className="mt-3 h-11 w-full text-sm font-medium underline underline-offset-4">
        {t("I am safe. Go back to the chat.", "Estoy a salvo. Volver al chat.")}
      </button>
    </div>
  );
}