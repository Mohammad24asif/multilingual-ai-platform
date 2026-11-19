import type { Language, ModelInfo } from "../api/types";
import { Badge } from "../components/Badge";
import { formatMb } from "../lib/format";
import { describeReason, licenceLabel, licenceTone } from "../lib/reasons";
import { languageLabel } from "../lib/scripts";

function ModelCard({ model }: { model: ModelInfo }) {
  const urls = model.evidence.urls ?? [];
  return (
    <li className="rounded-[10px] border border-rule bg-panel p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-semibold">{model.display_name}</h3>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone={licenceTone(model.licence.class)} title={model.licence.note}>
            {licenceLabel(model.licence.class)} · {model.licence.spdx}
          </Badge>
          <Badge tone={model.usable ? "ok" : "warn"}>{model.usable ? "Usable now" : "Blocked"}</Badge>
        </div>
      </div>
      <p className="mt-1 font-mono text-xs text-soft">{model.hf_repo}</p>

      {!model.usable && (
        <ul className="mt-3 list-disc pl-5 text-sm text-warn">
          {model.blocked_by.map((reason) => (
            <li key={reason}>{describeReason(reason)}</li>
          ))}
        </ul>
      )}

      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-5 gap-y-1 text-sm">
        <dt className="text-soft">Directions</dt>
        <dd>
          {model.source_languages.length} source and {model.target_languages.length} target languages
        </dd>
        <dt className="text-soft">Memory</dt>
        <dd>about {formatMb(model.estimated_ram_mb)} (estimate, not measured)</dd>
        <dt className="text-soft">Weights</dt>
        <dd>{model.downloaded === null ? "unknown" : model.downloaded ? "downloaded" : "not downloaded"}</dd>
        <dt className="text-soft">Revision</dt>
        <dd>{model.revision_pinned ? "pinned" : "not pinned"}</dd>
        <dt className="text-soft">In memory</dt>
        <dd>{model.state.replace("_", " ")}</dd>
      </dl>

      <p className="mt-3 text-sm">{model.evidence.coverage}</p>
      <p className="mt-1 text-xs text-soft">
        Checked {model.evidence.checked ?? "unknown date"}. Language codes verified against the tokenizer: {model.evidence.codes_verified ? "yes" : "not yet"}.
      </p>
      {urls.length > 0 && (
        <p className="mt-1 text-xs">
          {urls.map((url) => (
            <a key={url} href={url} target="_blank" rel="noreferrer" className="mr-3 text-accent underline">
              Source
            </a>
          ))}
        </p>
      )}
      {model.notes && <p className="mt-2 text-xs text-soft">{model.notes}</p>}
    </li>
  );
}

export function ModelsPage({ models, languages }: { models: ModelInfo[]; languages: Language[] }) {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-serif text-2xl font-semibold">Models and languages</h1>
        <p className="mt-1 text-sm text-soft">
          Everything here comes from the registry. Coverage is declared by the model authors; it is not a promise that every pair translates well.
        </p>
      </header>

      <section aria-labelledby="models-title">
        <h2 id="models-title" className="mb-3 text-lg font-semibold">
          Models
        </h2>
        <ul className="grid gap-4 lg:grid-cols-2">
          {models.map((model) => (
            <ModelCard key={model.id} model={model} />
          ))}
        </ul>
      </section>

      <section aria-labelledby="languages-title">
        <h2 id="languages-title" className="mb-3 text-lg font-semibold">
          Languages
        </h2>
        <div className="overflow-x-auto rounded-[10px] border border-rule bg-panel">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Languages and whether they can be a source or a target</caption>
            <thead className="border-b border-rule text-soft">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium">Language</th>
                <th scope="col" className="px-4 py-2 font-medium">Code</th>
                <th scope="col" className="px-4 py-2 font-medium">Script</th>
                <th scope="col" className="px-4 py-2 font-medium">Source</th>
                <th scope="col" className="px-4 py-2 font-medium">Target</th>
              </tr>
            </thead>
            <tbody>
              {languages.map((lang) => (
                <tr key={lang.code} className="border-b border-rule last:border-0">
                  <th scope="row" className="px-4 py-2 font-normal" lang={lang.code}>
                    {languageLabel(lang)}
                  </th>
                  <td className="px-4 py-2 font-mono text-xs">{lang.code}</td>
                  <td className="px-4 py-2">{lang.scripts.join(", ")}</td>
                  <td className="px-4 py-2">{lang.can_be_source ? "yes" : "no"}</td>
                  <td className="px-4 py-2">{lang.can_be_target ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
