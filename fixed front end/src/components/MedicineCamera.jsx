import { useEffect, useRef, useState } from "react";
import { Camera, Check, Loader2, X } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useLang } from "@/components/LanguageProvider";
import { DOC_LABELS } from "@/lib/sampleCases";
import { loc, speak } from "@/lib/loc";
import { api, connected } from "@/api/rexo";

// One still frame from the live video, as a JPEG blob (kept in memory, never saved).
const grabFrame = (video) => new Promise((resolve, reject) => {
  if (!video?.videoWidth) return reject(new Error("The camera isn't ready yet. Try again in a moment."));
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("Could not capture the picture."))), "image/jpeg", 0.92);
});

// Label details shown under the confirmation question (values are as read from the photo).
const FIELD_LABELS = {
  brand: { en: "Brand", es: "Marca" },
  strength: { en: "Strength", es: "Concentración" },
  dosage_form: { en: "Form", es: "Forma" },
  directions: { en: "Directions", es: "Indicaciones" },
  food_instruction: { en: "With food", es: "Con comida" },
  quantity: { en: "Quantity", es: "Cantidad" },
  refills: { en: "Refills", es: "Resurtidos" },
  discard_after: { en: "Discard after", es: "Desechar después de" },
};

export default function MedicineCamera({ data, onClose, onConfirmed }) {
  const { lang, t } = useLang();
  const videoRef = useRef(null);
  const [step, setStep] = useState("camera");
  const [denied, setDenied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(null);
  const [problem, setProblem] = useState("");
  const med = data.instructions.find((i) => i.kind === "medication");
  const details = (reading?.fields || []).filter((f) => FIELD_LABELS[f.field] && f.field !== "medication_name");
  const seen = med ? `${loc(med.name, lang)} ${typeof med.amount === "string" ? med.amount.split(",")[0] : ""}`.trim() : "";

  useEffect(() => {
    let stream;
    // High resolution matters: Tesseract can't read a label from the default 640x480 stream.
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1600 }, height: { ideal: 1200 } }, audio: false })
      .then((s) => { stream = s; if (videoRef.current) videoRef.current.srcObject = s; })
      .catch(() => setDenied(true));
    if (!navigator.mediaDevices) setDenied(true);
    return () => stream?.getTracks().forEach((track) => track.stop());
  }, []);

  // Connected: the backend reads the photo with OpenAI vision (one photo is enough), falling back to
  // local OpenCV + Tesseract. A local OCR reading needs two consecutive frames to agree on name +
  // strength before we offer a confirmation. Works for sample visits too.
  const readLabel = async () => {
    if (!connected) return setStep("confirm");
    setBusy(true);
    setProblem("");
    setReading(null);
    try {
      let previous = "";
      let last = null;
      for (let attempt = 0; attempt < 3; attempt++) {
        const frame = await grabFrame(videoRef.current);
        const result = await api.identifyMedicine(frame, lang, data.live ? data.caseId : undefined);
        last = result;
        if (result.engine === "openai-vision") {
          if (!result.found) break;
          setReading(result);
          setStep("confirm");
          return;
        }
        const key = result.found && result.strength_seen ? `${result.medication_name}:${result.strength_seen}` : "";
        if (key && key === previous) {
          setReading(result);
          setStep("confirm");
          return;
        }
        previous = key;
      }
      setProblem(last?.found
        ? t("The readings didn't agree on the strength. Move closer, reduce glare, and hold steady.", "Las lecturas no coincidieron en la concentración. Acérquese, reduzca el brillo y no se mueva.")
        : last?.confirm_prompt || t("Could not read the label.", "No se pudo leer la etiqueta."));
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
    // Sample visit: only quote the sample document when the label shows the same medicine.
    const sampleName = med ? loc(med.name, "en").toLowerCase() : "";
    if (reading && !(sampleName && (sampleName.includes(reading.medication_name) || reading.medication_name.includes(sampleName.split(" ")[0])))) {
      const other = t(
        `You confirmed ${reading.medication_name}. This medicine is not in this visit's documents. Ask your pharmacist about it.`,
        `Confirmó ${reading.medication_name}. Este medicamento no aparece en los documentos de esta visita. Pregunte a su farmacéutico.`
      );
      speak(other, lang);
      return onConfirmed({ role: "assistant", tag: "documents", text: other, quotes: [] });
    }
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
            {reading ? (
              <>
                <p className="text-xl">{reading?.confirm_prompt}</p>
                {details.length > 0 && (
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-xl bg-secondary px-4 py-3 text-sm">
                    {details.map((f) => (
                      <div key={f.field} className="contents">
                        <dt className="font-semibold">{loc(FIELD_LABELS[f.field], lang)}</dt>
                        <dd>{f.value}</dd>
                      </div>
                    ))}
                  </dl>
                )}
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