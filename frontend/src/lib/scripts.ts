import type { Language } from "../api/types";

// A small colour per writing system, so a glance shows when a translation crosses scripts.
// Colour is decoration only: the language name is always written out next to it.
const SCRIPT_COLORS: Record<string, string> = {
  Latin: "#5f6f7d",
  Telugu: "#0b7a75",
  Devanagari: "#b4691f",
  Tamil: "#a23b52",
  Kannada: "#6a4fb3",
  Malayalam: "#2f7d3e",
  Bengali: "#b0457a",
  Gujarati: "#9a7b00",
  Gurmukhi: "#c0562b",
  Arabic: "#2b6cb0",
};
const FALLBACK = "#7a8794";

export function scriptColor(script: string | null | undefined): string {
  return (script && SCRIPT_COLORS[script]) || FALLBACK;
}

export function languageLabel(lang: Pick<Language, "name" | "native_name">): string {
  return lang.native_name === lang.name ? lang.name : `${lang.native_name} · ${lang.name}`;
}

export function primaryScript(lang: Pick<Language, "scripts">): string | undefined {
  return lang.scripts[0];
}

export function indexByCode(languages: Language[]): Record<string, Language> {
  return Object.fromEntries(languages.map((lang) => [lang.code, lang]));
}
