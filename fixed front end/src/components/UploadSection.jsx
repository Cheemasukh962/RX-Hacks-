import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { ShieldCheck } from "lucide-react";
import DocumentSlot from "@/components/DocumentSlot";
import { Checkbox } from "@/components/ui/checkbox";
import { useLang } from "@/components/LanguageProvider";

export const UPLOADED_KEY = "rexo-uploaded";

export default function UploadSection() {
  const { t } = useLang();
  const [avs, setAvs] = useState("");
  const [note, setNote] = useState("");
  const [consent, setConsent] = useState(false);
  const navigate = useNavigate();
  const ready = avs.trim() && note.trim() && consent;
  const finish = () => {
    localStorage.setItem(UPLOADED_KEY, "1");
    navigate({ to: "/visits" });
  };

  return (
    <section id="upload" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-16 sm:px-6 sm:py-20">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <h2 className="font-display text-4xl font-normal leading-[1.1] tracking-tight">{t("Upload my documents", "Subir mis documentos")}</h2>
        <p className="max-w-sm text-muted-foreground">{t("Add both documents from your visit. REXO compares them.", "Añada los dos documentos de su visita. REXO los compara.")}</p>
      </div>

      <div className="mt-10 grid gap-4 md:grid-cols-2">
        <DocumentSlot label={t("After-visit summary", "Resumen de la visita")} value={avs} onChange={setAvs} />
        <DocumentSlot label={t("Clinical note", "Nota clínica")} value={note} onChange={setNote} />
      </div>

      <p className="mt-6 flex items-start gap-2 text-stone">
        <ShieldCheck className="mt-1 h-5 w-5 shrink-0 text-sage" aria-hidden="true" />
        {t("Names, birth dates and record numbers are removed before anything is read. The number removed shows here after reading.", "Los nombres, fechas de nacimiento y números de registro se eliminan antes de leer. La cantidad eliminada aparece aquí después.")}
      </p>

      <div className="mt-6 flex items-start gap-3">
        <Checkbox id="consent" checked={consent} onCheckedChange={(v) => setConsent(v === true)} className="mt-1 h-5 w-5" />
        <label htmlFor="consent" className="text-base">{t("These are fictional documents, or I have consent to use them.", "Estos documentos son ficticios, o tengo permiso para usarlos.")}</label>
      </div>

      <button type="button" disabled={!ready} onClick={finish} className="mt-8 h-14 w-full rounded-full bg-primary px-8 text-base font-semibold text-primary-foreground transition-colors duration-200 hover:bg-signal-600 disabled:bg-secondary disabled:text-stone sm:w-auto">
        {t("Read my documents", "Leer mis documentos")}
      </button>

    </section>
  );
}