import { useEffect, useRef, useState } from "react";
import { Camera, Check, Loader2, X } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useLang } from "@/components/LanguageProvider";
import { DOC_LABELS } from "@/lib/sampleCases";
import { loc, speak } from "@/lib/loc";
import { api } from "@/api/rexo";

// One still frame from the live video, as a JPEG blob (kept in memory, never saved).
const grabFrame = (video) => new Promise((resolve, reject) => {
  if (!video?.videoWidth) return reject(new Error("The camera isn't ready yet. Try again in a moment."));
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("Could not capture the picture."))), "image/jpeg", 0.92);
});

export default function MedicineCamera({ data, onClose, onConfirmed }) {
  const { lang, t } = useLang();
  const videoRef = useRef(null);
  const [step, setStep] = useState("camera");
  const [denied, setDenied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(null);
  const [problem, setProblem] = useState("");
  const med = data.instructions.find((i) => i.kind === "medication");
  const seen = med ? `${loc(med.name, lang)} ${typeof med.amount === "string" ? med.amount.split(",")[0] : ""}`.trim() : "";

  useEffect(() => {
    let stream;
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => { stream = s; if (videoRef.current) videoRef.current.srcObject = s; })
      .catch(() => setDenied(true));
    if (!navigator.mediaDevices) setDenied(true);
    return () => stream?.getTracks().forEach((track) => track.stop());
  }, []);

  // Live: read the label with the backend's OpenCV + OCR, then confirm before saying anything.
  const readLabel = async () => {
    if (!data.live) return setStep("confirm");
    setBusy(true);
    setProblem("");
    try {
      const frame = await grabFrame(videoRef.current);
      const result = await api.identifyMedicine(frame, lang, data.caseId);
      if (result.found) {
        setReading(result);
        setStep("confirm");
      } else {
        setProblem(result.confirm_prompt);
      }
    } catch (e) {
      setProblem(e.message);
    } finally {
      setBusy(false);
    }
  };

  const confirmLive = async () => {
    setBusy(true);
    try {
      const intro = await api.medicineIntro({ medicationName: reading.medication_name, caseId: data.caseId, language: lang });
      speak(intro.spoken_text, lang);
      onConfirmed({
        role: "assistant", tag: "documents", text: intro.spoken_text,
        quotes: (intro.citations || []).map((c) => ({ doc: c.document_id?.startsWith("avs") ? "avs" : "note", quote: c.quote })),
      });
    } catch (e) {
      setProblem(e.message);
      setBusy(false);
    }
  };

  const confirm = () => {
    if (data.live) return confirmLive();
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
          <div className="space-y-3">
            {problem && <p role="alert" className="rounded-xl bg-caution-soft px-4 py-3">{problem}</p>}
            <button type="button" onClick={readLabel} disabled={busy || denied} className="inline-flex h-14 w-full items-center justify-center gap-2 rounded-full bg-primary text-base font-semibold text-primary-foreground hover:bg-signal-600 disabled:opacity-60">
              {busy ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <Camera className="h-5 w-5" aria-hidden="true" />}
              {busy ? t("Reading the label…", "Leyendo la etiqueta…") : t("Read the label", "Leer la etiqueta")}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {data.live ? (
              <>
                <p className="text-xl">{reading?.confirm_prompt}</p>
                {reading?.strength_mismatch && (
                  <p className="rounded-xl bg-caution-soft px-4 py-3">{t(`The strength on the label differs from your documents (${(reading.documented_strengths || []).join(", ")}). Ask your care team or pharmacist.`, `La concentración de la etiqueta no coincide con sus documentos (${(reading.documented_strengths || []).join(", ")}). Pregunte a su equipo o farmacéutico.`)}</p>
                )}
                {problem && <p role="alert" className="rounded-xl bg-caution-soft px-4 py-3">{problem}</p>}
              </>
            ) : (
              <>
                <p className="rounded-xl bg-secondary px-4 py-3 text-sm text-clay">{t("Demo mode: label reading isn't connected, so this is the sample result, not a reading of your photo.", "Modo demo: la lectura de etiquetas no está conectada. Este es el resultado de ejemplo, no una lectura de su foto.")}</p>
                <p className="text-xl">{t("I see", "Veo")} <strong>{seen}</strong>. {t("Is that right?", "¿Es correcto?")}</p>
              </>
            )}
            <div className="flex gap-3">
              <button type="button" onClick={confirm} disabled={busy} className="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-foreground font-semibold text-background">
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