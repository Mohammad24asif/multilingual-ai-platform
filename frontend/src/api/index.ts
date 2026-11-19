import { createApi } from "./client";

// Empty base URL = same origin (Vite proxies /api in development; nginx does in Docker).
export const api = createApi({ baseUrl: import.meta.env?.VITE_API_BASE ?? "" });
