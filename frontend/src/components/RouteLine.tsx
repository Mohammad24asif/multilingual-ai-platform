import type { ReactNode } from "react";
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

/** The route a translation took: language -> model (with its licence) -> language, with any pivot spelled out. */
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
  const nodes: ReactNode[] = [];
  legs.forEach((leg, index) => {
    if (index === 0) nodes.push(<LangChip key={`from-${index}`} code={leg.source} language={languages[leg.source]} />);
    nodes.push(<ModelNode key={`model-${index}`} modelId={leg.modelId} model={models[leg.modelId]} />);
    nodes.push(<LangChip key={`to-${index}`} code={leg.target} language={languages[leg.target]} />);
  });
  return (
    <div>
      <ol aria-label="Translation route" className="flex flex-wrap items-center gap-y-2">
        {nodes.map((node, index) => (
          <li key={index} className="flex items-center">
            {index > 0 && <span aria-hidden="true" className="mx-1.5 h-px w-5 bg-rule" />}
            {node}
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
