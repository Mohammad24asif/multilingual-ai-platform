import type { LicenceClass } from "../api/types";

const REASONS: Record<string, string> = {
  disabled: "Switched off in the settings.",
  remote_code_not_reviewed: "Runs code from its model repository; the revision is not pinned, reviewed and allowed yet.",
  licence_unverified: "Licence not verified yet (required in commercial mode).",
  licence_unknown: "Licence is unknown.",
  exceeds_ram_budget: "Needs more memory than the configured budget.",
  not_downloaded: "Weights are not downloaded yet.",
  source_language_not_supported: "Does not support the source language.",
  target_language_not_supported: "Does not support the target language.",
};

export function describeReason(code: string): string {
  if (code.startsWith("licence_not_allowed:")) {
    const klass = code.split(":")[1];
    return klass === "non_commercial"
      ? "Research-only licence; not allowed in commercial mode."
      : `Licence class "${klass}" is not allowed in commercial mode.`;
  }
  return REASONS[code] ?? code;
}

export function licenceLabel(klass: LicenceClass): string {
  switch (klass) {
    case "permissive":
      return "Permissive licence";
    case "non_commercial":
      return "Research use only";
    case "restricted":
      return "Restricted terms";
    default:
      return "Licence unknown";
  }
}

export function licenceTone(klass: LicenceClass): "ok" | "warn" | "bad" | "neutral" {
  switch (klass) {
    case "permissive":
      return "ok";
    case "non_commercial":
    case "restricted":
      return "warn";
    default:
      return "bad";
  }
}

const WARNINGS: Record<string, string> = {
  target_script_mismatch: "The output is not mostly in the expected script. The model may have answered in the wrong language.",
  source_copied: "Some sentences came back unchanged.",
  length_ratio_outlier: "Some translations are much longer or shorter than their source sentence.",
};

export function describeWarning(code: string, detail: string): string {
  return WARNINGS[code] ?? detail;
}
