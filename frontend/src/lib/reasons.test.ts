import { describe, expect, it } from "vitest";
import { describeReason, describeWarning, licenceLabel, licenceTone } from "./reasons";

describe("reason and licence wording", () => {
  it("explains blocking reasons in plain language", () => {
    expect(describeReason("remote_code_not_reviewed")).toContain("reviewed");
    expect(describeReason("licence_not_allowed:non_commercial")).toContain("Research-only");
    expect(describeReason("licence_not_allowed:restricted")).toContain("restricted");
    expect(describeReason("something_new")).toBe("something_new");
  });

  it("labels licence classes and picks a tone", () => {
    expect(licenceLabel("non_commercial")).toBe("Research use only");
    expect(licenceTone("permissive")).toBe("ok");
    expect(licenceTone("non_commercial")).toBe("warn");
    expect(licenceTone("unknown")).toBe("bad");
  });

  it("prefers the friendly warning text and falls back to the server detail", () => {
    expect(describeWarning("source_copied", "x")).toContain("unchanged");
    expect(describeWarning("new_code", "server detail")).toBe("server detail");
  });
});
