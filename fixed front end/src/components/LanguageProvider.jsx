import { createContext, useContext, useState } from "react";

const LanguageContext = createContext({ lang: "en", setLang: () => {}, t: (en) => en });

export const useLang = () => useContext(LanguageContext);

export default function LanguageProvider({ children }) {
  const [lang, setLang] = useState("en");
  const t = (en, es) => (lang === "es" && es ? es : en);
  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}