import { useEffect, useState } from "react";
import { Phone } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useLang } from "@/components/LanguageProvider";
import { DOC_LABELS } from "@/lib/sampleCases";

const KEY = "rexo-doctor-phone";

export default function CallDoctor({ finding, onClose }) {
  const { lang, t } = useLang();
  const [phone, setPhone] = useState("");
  useEffect(() => setPhone(localStorage.getItem(KEY) || ""), []);
  const digits = phone.replace(/[^\d+]/g, "");
  const button = "inline-flex h-12 items-center justify-center gap-2 rounded-full px-6 text-base font-semibold";

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader className="text-left">
          <DialogTitle className="font-display text-3xl font-normal">{t("Call my doctor", "Llamar a mi médico")}</DialogTitle>
          <DialogDescription>{t("REXO never places calls. It opens your phone's own dialer.", "REXO nunca hace llamadas. Abre el marcador de su propio teléfono.")}</DialogDescription>
        </DialogHeader>
        <label className="block text-sm font-semibold">
          {t("Your doctor's office phone number", "Teléfono del consultorio de su médico")}
          <Input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="(555) 555-0100" className="mt-1 h-12 text-base" />
        </label>
        <p className="text-sm text-stone">{t("It's usually printed at the top of your after-visit summary. It is saved on this device only.", "Suele estar impreso arriba en su resumen de la visita. Se guarda solo en este dispositivo.")}</p>
        {finding && (
          <div className="space-y-2">
            <p className="text-sm font-semibold">{t("What to ask", "Qué preguntar")}</p>
            <p>{finding.title[lang]} {t("Which one applies to me?", "¿Cuál aplica a mí?")}</p>
            {finding.quotes.map((q, i) => (
              <blockquote key={i} className="border-l-2 border-caution bg-caution-soft px-3 py-2 font-display italic">{DOC_LABELS[q.doc][lang]}: "{q.quote}"</blockquote>
            ))}
          </div>
        )}
        {digits ? (
          <a href={`tel:${digits}`} onClick={() => localStorage.setItem(KEY, phone)} className={`${button} bg-primary text-primary-foreground hover:bg-signal-600`}>
            <Phone className="h-5 w-5" aria-hidden="true" />
            {t("Call now", "Llamar ahora")}
          </a>
        ) : (
          <p className={`${button} bg-secondary text-stone`}>{t("Enter a number to call", "Escriba un número para llamar")}</p>
        )}
      </DialogContent>
    </Dialog>
  );
}