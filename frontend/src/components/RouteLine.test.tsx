import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Language, ModelInfo } from "../api/types";
import { RouteLine } from "./RouteLine";

// React inserts <!-- --> between adjacent text nodes when rendering to a string.
const plain = (html: string) => html.replace(/<!-- -->/g, "");

const languages: Record<string, Language> = {
  te: { code: "te", name: "Telugu", native_name: "తెలుగు", scripts: ["Telugu"], rtl: false, can_be_source: true, can_be_target: true },
  en: { code: "en", name: "English", native_name: "English", scripts: ["Latin"], rtl: false, can_be_source: true, can_be_target: true },
  hi: { code: "hi", name: "Hindi", native_name: "हिन्दी", scripts: ["Devanagari"], rtl: false, can_be_source: true, can_be_target: true },
};
const nllb = {
  id: "nllb-200-distilled-600m",
  display_name: "NLLB-200 distilled (600M)",
  licence: { spdx: "CC-BY-NC-4.0", class: "non_commercial", verified: true, note: "Research use only." },
} as ModelInfo;

describe("RouteLine", () => {
  it("shows language, model with licence, language", () => {
    const html = renderToString(
      <RouteLine legs={[{ source: "te", target: "en", modelId: nllb.id }]} languages={languages} models={{ [nllb.id]: nllb }} />,
    );
    expect(html).toContain("తెలుగు");
    expect(html).toContain("NLLB-200 distilled (600M)");
    expect(html).toContain("CC-BY-NC-4.0");
    expect(html).toContain("research only");
    expect(html).toContain('aria-label="Translation route"');
  });

  it("spells out a pivot through English", () => {
    const html = renderToString(
      <RouteLine
        legs={[
          { source: "te", target: "en", modelId: nllb.id },
          { source: "en", target: "hi", modelId: nllb.id },
        ]}
        languages={languages}
        models={{ [nllb.id]: nllb }}
        pivotVia="en"
      />,
    );
    expect(plain(html)).toContain("Two-step translation through English");
    expect(html).toContain("हिन्दी");
  });

  it("still renders when a model is unknown to the registry listing", () => {
    const html = renderToString(<RouteLine legs={[{ source: "te", target: "en", modelId: "mystery" }]} languages={languages} models={{}} />);
    expect(html).toContain("mystery");
  });
});
