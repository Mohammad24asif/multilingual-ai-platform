// Mirrors the backend's JSON (see backend/app/presentation.py). The API never returns confidence scores.

export type LicenceClass = "permissive" | "non_commercial" | "restricted" | "unknown";

export interface Licence {
  spdx: string;
  class: LicenceClass;
  verified: boolean;
  note: string;
}

export interface Language {
  code: string;
  name: string;
  native_name: string;
  scripts: string[];
  rtl: boolean;
  can_be_source: boolean;
  can_be_target: boolean;
}

export interface ModelInfo {
  id: string;
  display_name: string;
  family: string;
  task: string;
  hf_repo: string;
  revision: string | null;
  revision_pinned: boolean;
  licence: Licence;
  requires_remote_code: boolean;
  params_millions: number | null;
  estimated_ram_mb: number | null;
  ram_estimate_basis: string;
  source_languages: string[];
  target_languages: string[];
  priority: number;
  priority_basis: string;
  enabled: boolean;
  downloaded: boolean | null;
  state: string;
  last_error_code: string | null;
  usable: boolean;
  blocked_by: string[];
  evidence: { checked?: string; coverage?: string; urls?: string[]; codes_verified?: boolean };
  notes: string;
}

export interface LegView {
  source: string;
  target: string;
  model_id: string;
  model_revision: string | null;
  licence: string;
  device: string;
  units: number;
  batches: number;
  split_units: Record<string, number>;
  token_counts: string;
  queue_wait_ms: number;
  load_ms: number;
  inference_ms: number;
}

export interface ResultWarning {
  code: string;
  detail: string;
  count: number;
}

export interface DetectionInfo {
  status: string;
  method: string | null;
  script: string | null;
  notes: string[];
}

export interface TranslateResponse {
  translation: string;
  source_language: string;
  source_detection: DetectionInfo | null;
  target_language: string;
  pivot: boolean;
  pivot_via: string | null;
  legs: LegView[];
  segments: number;
  input_chars: number;
  output_chars: number;
  warnings: ResultWarning[];
  timings_ms: Record<string, number>;
  normalization: Record<string, number>;
  note: string;
}

export interface Readiness {
  ready: boolean;
  executor_alive: boolean;
  usable_models: string[];
  loaded_models: string[];
  problems: string[];
}

export interface SystemOverview {
  hardware: {
    python: string;
    platform: string;
    cpu_count_logical: number | null;
    cpu_count_physical: number | null;
    ram_total_mb: number | null;
    ram_available_mb: number | null;
    torch: { installed: boolean; version?: string; cuda_available: boolean; cuda_device?: string };
  };
  device: string;
  queue: { depth: number; capacity: number; running: boolean; completed: number; failed: number; rejected: number; cancelled: number };
  policy: {
    licence_mode: string;
    ram_budget_mb: number | null;
    max_loaded_models: number;
    downloads_allowed: boolean;
    inference_timeout_s: number;
    max_input_chars: number;
  };
}

export interface Problem {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  request_id?: string;
  [key: string]: unknown;
}

export interface TranslateRequest {
  text: string;
  target_language: string;
  source_language?: string;
  model_id?: string | null;
  allow_pivot?: boolean;
  num_beams?: number | null;
}

export interface RouteLegPlan {
  source: string;
  target: string;
  model_id: string;
  model_name: string;
  licence: string;
  licence_class: LicenceClass;
  considered: { model_id: string; accepted: boolean; reasons: string[] }[];
}

export interface RouteResponse {
  pivot: boolean;
  pivot_via: string | null;
  legs: RouteLegPlan[];
}
