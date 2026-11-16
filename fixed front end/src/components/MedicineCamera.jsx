import { useEffect, useRef, useState } from "react";
import { Camera, Check, X } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useLang } from "@/components/LanguageProvider";
import { DOC_LABELS } from "@/lib/sampleCases";
import { loc, speak } from "@/lib/loc";

export default function MedicineCamera({ data, onClose, onConfirmed }) {
  const { lang, t } = useLang();
  const videoRef = useRef(null);
  const [step, setStep] = useState("camera");
  const [denied, setDenied] = useState(false);
  const med = data.instructions.find((i) => i.kind === "medication");
  const seen = `${loc(med.name, lang)} ${typeof med.amount === "string" ? med.amount.split(",")[0] : ""}`.trim();

  useEffect(() => {
    let stream;
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => { stream = s; if (videoRef.current) videoRef.current.srcObject = s; })
      .catch(() => setDenied(true));
    if (!navigator.mediaDevices) setDenied(true);
    return () => stream?.getTracks().forEach((track) => track.stop());
  }, []);

  const confirm = () => {
    const text = t(
      `This is ${seen}. Your ${DOC_LABELS[med.evidence.doc].en.toLowerCase()} says: "${med.evidence.quote}".`,
      `Esto es ${seen}. Su ${DOC_LABELS[med.evidence.doc].es.toLowerCase()} dice: "${med.evidence.quote}".`
    );
    speak(text, lang);
    onConfirmed({ role: "assistant", tag: "documents", text, quotes: [med.evidence] });
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader className="text-left">
          <DialogTitle className="font-display text-3xl font-normal">{t("Show me your medicine", "Muéstreme su medicina")}</DialogTitle>
          <DialogDescription>{t("Hold the label up to the camera. Labels only, never loose pills.", "Acerque la etiqueta a la cámara. Solo etiquetas, nunca pastillas sueltas.")}</DialogDescription>
        </DialogHeader>
        <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-charcoal">
          {denied ? (
            <p className="flex h-full items-center justify-center p-6 text-center text-background">{t("The camera isn't available. You can type the medicine name in the chat instead.", "La cámara no está disponible. Puede escribir el nombre de la medicina en el chat.")}</p>
          ) : (
            <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
          )}
        </div>
        {step === "camera" ? (
          <button type="button" onClick={() => setStep("confirm")} className="inline-flex h-14 items-center justify-center gap-2 rounded-full bg-primary text-base font-semibold text-primary-foreground hover:bg-signal-600">
            <Camera className="h-5 w-5" aria-hidden="true" />
            {t("Read the label", "Leer la etiqueta")}
          </button>
        ) : (
          <div className="space-y-4">
            <p className="rounded-xl bg-secondary px-4 py-3 text-sm text-clay">{t("Demo mode: label reading isn't connected, so this is the sample result, not a reading of your photo.", "Modo demo: la lectura de etiquetas no está conectada. Este es el resultado de ejemplo, no una lectura de su foto.")}</p>
            <p className="text-xl">{t("I see", "Veo")} <strong>{seen}</strong>. {t("Is that right?", "¿Es correcto?")}</p>
            <div className="flex gap-3">
              <button type="button" onClick={confirm} className="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-foreground font-semibold text-background">
                <Check className="h-5 w-5" aria-hidden="true" />{t("Yes", "Sí")}
              </button>
              <button type="button" onClick={() => setStep("camera")} className="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-full border border-foreground font-semibold">
                <X className="h-5 w-5" aria-hidden="true" />{t("No, try again", "No, intentar de nuevo")}
              </button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}