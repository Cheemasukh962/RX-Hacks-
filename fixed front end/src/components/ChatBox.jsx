import { useEffect, useRef, useState } from "react";
import { Image as ImageIcon, Loader2, SendHorizontal } from "lucide-react";
import ChatMessage from "@/components/ChatMessage";
import MicButton from "@/components/MicButton";
import UrgentPanel from "@/components/UrgentPanel";
import { useLang } from "@/components/LanguageProvider";
import useDictation from "@/hooks/useDictation";
import { answer, isUrgent } from "@/lib/demoChat";
import { loc, speak } from "@/lib/loc";
import { useServerFn } from "@tanstack/react-start";
import ChatSettings from "@/components/ChatSettings";
import { generateVisual } from "@/lib/visual-fns";
import { cn } from "@/lib/utils";
import { api } from "@/api/rexo";

const TIER_TAG = { documents: "documents", drug_reference: "general", web: "web", unclear: "unclear" };
const docKind = (documentId) => (documentId?.startsWith("avs") ? "avs" : "note");

export default function ChatBox({ data, altered, messages, setMessages, onEmail, onCall, settings, setSettings }) {
  const { lang, t } = useLang();
  const draw = useServerFn(generateVisual);
  const [input, setInput] = useState("");
  const [urgent, setUrgent] = useState(false);
  const [pending, setPending] = useState(false);
  const dictation = useDictation(lang, setInput);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, urgent]);

  const firstMed = data.instructions.find((i) => i.kind === "medication");
  const suggestions = data.id === "meloxicam" || data.riskKey === "meloxicam"
    ? [t("What does meloxicam do?", "¿Para qué sirve el meloxicam?"), t("What if I take it on an empty stomach?", "¿Y si lo tomo con el estómago vacío?"), t("Can I take ibuprofen with it?", "¿Puedo tomar ibuprofeno con él?"), t("Which dose is right?", "¿Cuál dosis es la correcta?")]
    : firstMed ? [t(`What do my documents say about ${loc(firstMed.name, lang)}?`, `¿Qué dicen mis documentos sobre ${loc(firstMed.name, lang)}?`), t("Which one is right?", "¿Cuál es la correcta?")] : [t("What should I do next?", "¿Qué debo hacer ahora?")];

  const send = async (text) => {
    const q = text.trim();
    if (!q || pending) return;
    dictation.stop();
    setInput("");
    const mine = { role: "user", text: q };
    if (isUrgent(q)) {
      setMessages((m) => [...m, mine]);
      return setUrgent(true);
    }
    if (!data.live) {
      const reply = answer(data, q, lang, altered);
      if (settings.autoRead) speak(reply.text, lang);
      return setMessages((m) => [...m, mine, { role: "assistant", ...reply }]);
    }
    // Live: the backend answers from this visit's documents, then the drug fact sheet, then a web search.
    setMessages((m) => [...m, mine]);
    setPending(true);
    try {
      const history = [...messages, mine].slice(-20).map((m) => ({ role: m.role, content: m.text }));
      const r = await api.chat({
        caseId: altered && data.alteredCaseId ? data.alteredCaseId : data.caseId,
        language: lang,
        level: settings.level || "normal",
        messages: history,
      });
      if (r.urgent) return setUrgent(true);
      const reply = {
        role: "assistant",
        tag: TIER_TAG[r.tier] || "unclear",
        text: r.answer,
        quotes: (r.citations || []).map((c) => ({ doc: docKind(c.document_id), quote: c.quote })),
        sources: r.sources || [],
        offerEmail: r.offer_email,
      };
      if (settings.autoRead) speak(reply.text, lang);
      setMessages((m) => [...m, reply]);
    } catch (error) {
      setMessages((m) => [...m, { role: "assistant", tag: "unclear", text: error.message, offerEmail: false }]);
    } finally {
      setPending(false);
    }
  };

  const setVisual = (i, visual) => setMessages((m) => m.map((x, j) => (j === i ? { ...x, visual } : x)));
  const makeVisual = async (i) => {
    setVisual(i, { loading: true });
    try {
      setVisual(i, await draw({ data: { text: messages[i].text.slice(0, 600) } }));
    } catch {
      setVisual(i, { failed: true });
    }
  };

  // The picture button in the question bar draws for the most recent answer.
  const lastIndex = messages.findLastIndex((m) => m.role === "assistant");
  const last = messages[lastIndex];
  const canDraw = !!last && last.tag !== "unclear" && !last.visual?.url && !last.visual?.loading;
  const visualLabel = t("See a visual for the last answer", "Ver una imagen de la última respuesta");

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className={cn("flex-1 space-y-4 overflow-y-auto p-5", settings.largeText && "text-xl")}>
        {messages.length === 0 && (
          <div className="space-y-2">
            {suggestions.map((s) => (
              <button key={s} type="button" onClick={() => send(s)} className="block min-h-11 w-full rounded-xl border border-border bg-card px-4 py-3 text-left transition-colors duration-200 hover:border-foreground">
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => <ChatMessage key={i} message={m} onEmail={onEmail} onCall={onCall} onVisual={() => makeVisual(i)} />)}
        {pending && (
          <p role="status" className="flex items-center gap-2 text-sm text-stone">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            {t("REXO is checking your documents…", "REXO está revisando sus documentos…")}
          </p>
        )}
        {urgent && <UrgentPanel onResume={() => setUrgent(false)} />}
        <div ref={endRef} />
      </div>
      {!urgent && (
        <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="space-y-3 border-t border-border p-4">
          <MicButton dictation={dictation} large />
          <div className="flex gap-2">
            <ChatSettings settings={settings} onChange={setSettings} />
            <button type="button" onClick={() => makeVisual(lastIndex)} disabled={!canDraw} title={visualLabel} aria-label={visualLabel} className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-input bg-card disabled:text-stone/50">
              {last?.visual?.loading ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <ImageIcon className="h-5 w-5" aria-hidden="true" />}
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t("Or type your question", "O escriba su pregunta")}
              aria-label={t("Your question", "Su pregunta")}
              className="h-12 min-w-0 flex-1 rounded-full border border-input bg-card px-5 text-base"
            />
            <button type="submit" aria-label={t("Send", "Enviar")} className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-foreground text-background">
              <SendHorizontal className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </form>
      )}
    </div>
  );
}