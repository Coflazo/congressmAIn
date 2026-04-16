import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import nl from "./nl.json";
import pl from "./pl.json";
import tr from "./tr.json";
import uk from "./uk.json";

i18n.use(initReactI18next).init({
  resources: {
    nl: { translation: nl },
    en: { translation: en },
    tr: { translation: tr },
    pl: { translation: pl },
    uk: { translation: uk },
  },
  lng: "nl",
  fallbackLng: "nl",
  interpolation: { escapeValue: false },
});

export default i18n;
