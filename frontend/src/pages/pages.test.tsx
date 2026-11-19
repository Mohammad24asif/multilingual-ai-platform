import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Language, ModelInfo } from "../api/types";
import { ModelsPage } from "./ModelsPage";
import { TranslatePage } from "./TranslatePage";

// React inserts <!-- --> between adjacent text nodes when rendering to a string.
const plain = (html: string) => html.replace(/<!-- -->/g, "");

const languages: Language[] = [
  { code: "en", name: "English", native_name: "English", scripts: ["Latin"], rtl: false, can_be_source: true, can_be_target: true },
  { code: "te", name: "Telugu", native_name: "తెలుగు", scripts: ["Telugu"], rtl: false, can_be_source: true, can_be_target: true },
  { code: "ur", name: "Urdu", native_name: "اردو", scripts: ["Arabic"], rtl: true, can_be_source: true, can_be_target: false },
];

function model(overrides: Partial<ModelInfo>): ModelInfo {
  return {
    id: "m1", display_name: "Model One", family: "nllb", task: "translate", hf_repo: "org/model-one", revision: null, revision_pinned: false,
    licence: { spdx: "MIT", class: "permissive", verified: true, note: "" }, requires_remote_code: false, params_millions: 600, estimated_ram_mb: 3000,
    ram_estimate_basis: "estimate", source_languages: ["en", "te"], target_languages: ["en", "te"], priority: 10, priority_basis: "editorial", enabled: true,
    downloaded: true, state: "not_loaded", last_error_code: null, usable: true, blocked_by: [], evidence: { checked: "2026-11-16", coverage: "Declared coverage.", urls: ["https://example.org/card"], codes_verified: false }, notes: "", ...overrides,
  };
}

describe("TranslatePage (server-rendered smoke test)", () => {
  const html = renderToString(<TranslatePage languages={languages} models={[model({}), model({ id: "m2", display_name: "Blocked Model", usable: false })]} maxChars={20000} />);

  it("renders labelled controls", () => {
    expect(html).toContain("Text to translate");
    expect(html).toContain("Detect language");
    expect(html).toContain("Swap languages");
    expect(plain(html)).toContain("0 / 20,000 characters");
  });

  it("offers only languages that can be targets in the target list and only usable models", () => {
    const target = html.slice(html.indexOf('id="target-language"'), html.indexOf("</select>", html.indexOf('id="target-language"')));
    expect(target).toContain("తెలుగు");
    expect(target).not.toContain("اردو");
    expect(html).toContain("Model One");
    expect(html).not.toContain("Blocked Model");
  });

  it("starts with the translate button disabled and an empty-state message", () => {
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Translate<\/button>/);
    expect(html).toContain("Your translation appears here.");
  });
});

describe("ModelsPage (server-rendered smoke test)", () => {
  it("shows licence, blocking reasons and evidence", () => {
    const blocked = model({ id: "it2", display_name: "IndicTrans2", usable: false, blocked_by: ["remote_code_not_reviewed", "disabled"], licence: { spdx: "CC-BY-NC-4.0", class: "non_commercial", verified: true, note: "" } });
    const html = renderToString(<ModelsPage models={[model({}), blocked]} languages={languages} />);
    expect(html).toContain("Research use only");
    expect(html).toContain("Blocked");
    expect(html).toContain("Switched off in the settings.");
    expect(plain(html)).toContain("Language codes verified against the tokenizer: not yet");
    expect(html).toContain("اردو");
  });
});
