import { describe, expect, it } from "vitest";
import type { Language } from "../api/types";
import { indexByCode, languageLabel, primaryScript, scriptColor } from "./scripts";

const telugu: Language = { code: "te", name: "Telugu", native_name: "తెలుగు", scripts: ["Telugu"], rtl: false, can_be_source: true, can_be_target: true };
const english: Language = { code: "en", name: "English", native_name: "English", scripts: ["Latin"], rtl: false, can_be_source: true, can_be_target: true };

describe("scripts helpers", () => {
  it("labels a language with its native name and English name", () => {
    expect(languageLabel(telugu)).toBe("తెలుగు · Telugu");
    expect(languageLabel(english)).toBe("English");
  });

  it("maps scripts to colours and falls back for unknown scripts", () => {
    expect(scriptColor("Telugu")).toBe("#0b7a75");
    expect(scriptColor("Klingon")).toBe(scriptColor(undefined));
  });

  it("finds the primary script and indexes languages by code", () => {
    expect(primaryScript(telugu)).toBe("Telugu");
    expect(indexByCode([telugu, english]).en).toBe(english);
  });
});
