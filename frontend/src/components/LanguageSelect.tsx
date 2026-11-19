import type { ChangeEvent } from "react";
import type { Language } from "../api/types";
import { languageLabel } from "../lib/scripts";

export function LanguageSelect({
  id,
  label,
  value,
  onChange,
  languages,
  autoLabel,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (code: string) => void;
  languages: Language[];
  autoLabel?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="text-sm text-soft">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event: ChangeEvent<HTMLSelectElement>) => onChange(event.target.value)}
        className="rounded-md border border-rule bg-panel px-2.5 py-1.5 text-sm text-ink"
      >
        {autoLabel && <option value="auto">{autoLabel}</option>}
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {languageLabel(lang)}
          </option>
        ))}
      </select>
    </div>
  );
}
