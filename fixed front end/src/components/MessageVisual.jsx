import { Image } from "@/components/ui/image";
import { useLang } from "@/components/LanguageProvider";

export default function MessageVisual({ visual }) {
  const { t } = useLang();
  if (visual?.failed) {
    return <p className="mt-3 text-sm text-stone" role="status">{t("I couldn't make a picture this time. Please try again.", "No pude crear una imagen esta vez. Inténtelo de nuevo.")}</p>;
  }
  if (!visual?.url) return null;
  return (
    <figure className="mt-3">
      <Image src={visual.url} alt={t("Illustration for this answer", "Ilustración para esta respuesta")} className="aspect-square w-full max-w-xs overflow-hidden rounded-xl" />
      <figcaption className="mt-1 text-sm text-stone">{t("Picture made by AI to illustrate this answer. Not a prediction for you.", "Imagen creada por IA para ilustrar esta respuesta. No es una predicción para usted.")}</figcaption>
    </figure>
  );
}