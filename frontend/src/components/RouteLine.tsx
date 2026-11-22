import type { Language, ModelInfo } from "../api/types";
import { licenceTone } from "../lib/reasons";
import { Badge } from "./Badge";
import { LangChip } from "./LangChip";

export interface RouteLeg {
  source: string;
  target: string;
  modelId: string;
}

function ModelNode({ modelId, model }: { modelId: string; model?: ModelInfo }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-2 rounded-md bg-panel2 px-2.5 py-1 text-sm">
      <span className="font-medium">{model?.display_name ?? modelId}</span>
      {model && (
        <Badge tone={licenceTone(model.licence.class)} title={model.licence.note}>
          {model.licence.spdx}
          {model.licence.class === "non_commercial" ? " · research only" : ""}
        </Badge>
      )}
    </span>
  );
}

function Arrow() {
  return (
    <span aria-hidden="true" className="text-soft">
      →
    </span>
  );
}

/** The route a translation took: language -> model (with its licence) -> language, one row per step, with any pivot spelled out. */
export function RouteLine({
  legs,
  languages,
  models,
  pivotVia,
}: {
  legs: RouteLeg[];
  languages: Record<string, Language>;
  models: Record<string, ModelInfo>;
  pivotVia?: string | null;
}) {
  const steps = legs.length > 1;
  return (
    <div>
      <ol aria-label="Translation route" className="space-y-2">
        {legs.map((leg, index) => (
          <li key={index} className="flex flex-wrap items-center gap-2">
            {steps && <span className="w-12 text-xs font-medium text-soft">Step {index + 1}</span>}
            <LangChip code={leg.source} language={languages[leg.source]} />
            <Arrow />
            <ModelNode modelId={leg.modelId} model={models[leg.modelId]} />
            <Arrow />
            <LangChip code={leg.target} language={languages[leg.target]} />
          </li>
        ))}
      </ol>
      {pivotVia && (
        <p className="mt-2 text-sm text-warn">
          Two-step translation through {languages[pivotVia]?.name ?? pivotVia}: the text was translated twice, so quality can be lower.
        </p>
      )}
    </div>
  );
}
