import { describe, expect, it } from "vitest";
import { ApiError, createApi } from "./client";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

describe("api client", () => {
  it("returns parsed JSON", async () => {
    const api = createApi({ fetchImpl: async () => json([{ code: "te" }]) });
    expect(await api.languages()).toEqual([{ code: "te" }]);
  });

  it("turns problem+json into an ApiError that keeps the extra fields", async () => {
    const problem = { type: "urn:x", title: "Source language could not be determined", status: 422, detail: "Choose it manually.", code: "language_ambiguous", candidates: ["hi", "mr"] };
    const api = createApi({ fetchImpl: async () => json(problem, 422) });
    const error = await api.translate({ text: "x", target_language: "en" }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("language_ambiguous");
    expect((error as ApiError).problem.candidates).toEqual(["hi", "mr"]);
  });

  it("explains network failures in friendly words", async () => {
    const api = createApi({ baseUrl: "http://127.0.0.1:8000", fetchImpl: async () => { throw new TypeError("fetch failed"); } });
    const error = (await api.models().catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe("network_error");
    expect(error.message).toContain("127.0.0.1:8000");
  });

  it("falls back to a generic problem when the error body is not JSON", async () => {
    const api = createApi({ fetchImpl: async () => new Response("<html>oops</html>", { status: 502 }) });
    const error = (await api.system().catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe("http_502");
    expect(error.status).toBe(502);
  });

  it("treats a 503 readiness answer as data, not an error", async () => {
    const body = { ready: false, executor_alive: true, usable_models: [], loaded_models: [], problems: ["No model downloaded"] };
    const api = createApi({ fetchImpl: async () => json(body, 503) });
    expect((await api.readiness()).ready).toBe(false);
  });

  it("sends a JSON body with the right headers and a trimmed base URL", async () => {
    let seenUrl = "";
    let seenInit: RequestInit | undefined;
    const api = createApi({
      baseUrl: "http://host/",
      fetchImpl: async (url, init) => {
        seenUrl = url;
        seenInit = init;
        return json({ translation: "ok" });
      },
    });
    await api.translate({ text: "Hello", target_language: "te", source_language: "en" });
    expect(seenUrl).toBe("http://host/api/v1/translate");
    expect(seenInit?.method).toBe("POST");
    expect(JSON.parse(String(seenInit?.body))).toEqual({ text: "Hello", target_language: "te", source_language: "en" });
    expect((seenInit?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("builds the route query string", async () => {
    let seenUrl = "";
    const api = createApi({ fetchImpl: async (url) => { seenUrl = url; return json({ pivot: false, pivot_via: null, legs: [] }); } });
    await api.route({ source: "kn", target: "en", allowPivot: true });
    expect(seenUrl).toBe("/api/v1/route?source=kn&target=en&allow_pivot=true");
  });

  it("lets the user cancel without wrapping the abort", async () => {
    const api = createApi({
      fetchImpl: (_url, init) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
        }),
    });
    const controller = new AbortController();
    const pending = api.translate({ text: "x", target_language: "te" }, controller.signal);
    controller.abort();
    const error = (await pending.catch((e: unknown) => e)) as Error;
    expect(error.name).toBe("AbortError");
  });
});
