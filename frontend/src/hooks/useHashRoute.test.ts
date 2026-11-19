import { describe, expect, it } from "vitest";
import { parseRoute } from "./useHashRoute";

describe("parseRoute", () => {
  it("understands the three pages and defaults to translate", () => {
    expect(parseRoute("#/models")).toBe("models");
    expect(parseRoute("#status")).toBe("status");
    expect(parseRoute("")).toBe("translate");
    expect(parseRoute("#/does-not-exist")).toBe("translate");
  });
});
