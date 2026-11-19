import type { Language } from "../api/types";
import { languageLabel, primaryScript, scriptColor } from "../lib/scripts";

export function LangChip({ code, language }: { code: string; language?: Language }) {
  const color = scriptColor(language ? primaryScript(language) : undefined);
  return (
    <span className="inline-flex items-center gap-2 rounded-md border border-rule bg-panel px-2.5 py-1 text-sm">
      <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
      <span lang={language ? code : undefined}>{language ? languageLabel(language) : code}</span>
      <span className="text-xs text-soft">{code}</span>
    </span>
  );
}
