import type { Language, ModelInfo, Problem, Readiness, RouteResponse, SystemOverview, TranslateRequest, TranslateResponse } from "./types";

export class ApiError extends Error {
  readonly problem: Problem;
  readonly status: number;

  constructor(problem: Problem) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.problem = problem;
    this.status = problem.status;
  }

  get code(): string {
    return this.problem.code;
  }
}

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface ApiOptions {
  baseUrl?: string;
  fetchImpl?: FetchLike;
  timeoutMs?: number;
}

interface RequestOptions {
  method?: string;
  body?: string;
  signal?: AbortSignal;
  acceptStatuses?: number[];
}

function networkProblem(baseUrl: string): Problem {
  const where = baseUrl || "this address";
  return {
    type: "urn:mlai:error:network_error",
    title: "Cannot reach the server",
    status: 0,
    detail: `The backend did not answer at ${where}. Start it with "uv run uvicorn app.main:create_app --factory" in the backend folder.`,
    code: "network_error",
  };
}

export function createApi(options: ApiOptions = {}) {
  const baseUrl = (options.baseUrl ?? "").replace(/\/$/, "");
  const doFetch: FetchLike = options.fetchImpl ?? ((input, init) => fetch(input, init));
  const timeoutMs = options.timeoutMs ?? 150_000; // the server gives up at 120 s by default

  async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const external = opts.signal;
    if (external) {
      if (external.aborted) controller.abort();
      else external.addEventListener("abort", () => controller.abort(), { once: true });
    }
    let response: Response;
    try {
      response = await doFetch(`${baseUrl}${path}`, {
        method: opts.method ?? "GET",
        body: opts.body,
        signal: controller.signal,
        headers: {
          Accept: "application/json, application/problem+json",
          ...(opts.body !== undefined ? { "Content-Type": "application/json" } : {}),
        },
      });
    } catch (cause) {
      if (external?.aborted) throw cause; // the user cancelled: the caller handles the AbortError
      throw new ApiError(networkProblem(baseUrl));
    } finally {
      clearTimeout(timer);
    }
    if (response.ok || (opts.acceptStatuses ?? []).includes(response.status)) {
      return (await response.json()) as T;
    }
    let problem: Problem;
    try {
      const parsed = (await response.json()) as Problem;
      if (typeof parsed?.code !== "string") throw new Error("not a problem document");
      problem = parsed;
    } catch {
      problem = {
        type: "about:blank",
        title: "Unexpected response",
        status: response.status,
        detail: `The server answered with status ${response.status}.`,
        code: `http_${response.status}`,
      };
    }
    throw new ApiError(problem);
  }

  return {
    languages: () => request<Language[]>("/api/v1/languages"),
    models: () => request<ModelInfo[]>("/api/v1/models"),
    system: () => request<SystemOverview>("/api/v1/system"),
    readiness: () => request<Readiness>("/api/v1/health/ready", { acceptStatuses: [503] }),
    route: (p: { source: string; target: string; modelId?: string; allowPivot?: boolean }) => {
      const query = new URLSearchParams({ source: p.source, target: p.target });
      if (p.modelId) query.set("model_id", p.modelId);
      if (p.allowPivot) query.set("allow_pivot", "true");
      return request<RouteResponse>(`/api/v1/route?${query.toString()}`);
    },
    translate: (body: TranslateRequest, signal?: AbortSignal) =>
      request<TranslateResponse>("/api/v1/translate", { method: "POST", body: JSON.stringify(body), signal }),
  };
}

export type Api = ReturnType<typeof createApi>;
