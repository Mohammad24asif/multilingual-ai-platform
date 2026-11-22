import { describe, expect, it } from "vitest";
import type { Problem } from "../api/types";
import { formatCount, formatMb, formatMs, hostname } from "./format";
import { problemCandidates, problemHint, problemPivotVia, problemSuggested, problemUnlisted } from "./problem";

const base: Problem = { type: "t", title: "T", status: 422, detail: "d", code: "c" };

describe("problem helpers", () => {
  it("reads candidate lists defensively", () => {
    expect(problemCandidates({ ...base, candidates: ["hi", "mr"] })).toEqual(["hi", "mr"]);
    expect(problemCandidates({ ...base, candidates: "nope" })).toEqual([]);
    expect(problemCandidates({ ...base, candidates: ["hi", 3] })).toEqual(["hi"]);
  });

  it("reads optional string fields", () => {
    expect(problemSuggested({ ...base, suggested: "ur" })).toBe("ur");
    expect(problemSuggested(base)).toBeNull();
    expect(problemPivotVia({ ...base, pivot_available_via: "en" })).toBe("en");
    expect(problemHint({ ...base, hint: "Run: x" })).toBe("Run: x");
    expect(problemUnlisted({ ...base, unlisted_candidates: ["Nepali"] })).toEqual(["Nepali"]);
  });
});

describe("formatters", () => {
  it("formats durations, counts and memory", () => {
    expect(formatMs(85.4)).toBe("85 ms");
    expect(formatMs(1234)).toBe("1.2 s");
    expect(formatCount(20000)).toBe("20,000");
    expect(formatMb(512)).toBe("512 MB");
    expect(formatMb(3000)).toBe("2.9 GB");
    expect(formatMb(null)).toBe("unknown");
    expect(hostname("https://huggingface.co/facebook/x")).toBe("huggingface.co");
    expect(hostname("not a url")).toBe("source");
  });
});
