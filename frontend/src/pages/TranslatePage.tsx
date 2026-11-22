import { Fragment, useCallback, useMemo, useRef, useState } from "react";
import type { ChangeEvent, KeyboardEvent } from "react";
import { api } from "../api";
import { ApiError } from "../api/client";
import type { Language, ModelInfo, TranslateResponse } from "../api/types";
import { Button } from "../components/Button";
import { LanguageSelect } from "../components/LanguageSelect";
import { Notice } from "../components/Notice";
import { RouteLine } from "../components/RouteLine";
import { formatCount, formatMs } from "../lib/format";
import { problemCandidates, problemHint, problemPivotVia, problemSuggested, problemUnlisted } from "../lib/problem";
import { describeWarning } from "../lib/reasons";
import { indexByCode, languageLabel } from "../lib/scripts";

type Phase = "idle" | "loading" | "done" | "error";

function ErrorPanel({
  error,
  byCode,
  onPickSource,
  onAllowPivot,
}: {
  error: ApiError;
  byCode: Record<string, Language>;
  onPickSource: (code: string) => void;
  onAllowPivot: () => void;
}) {
  const problem = error.problem;
  const candidates = problemCandidates(problem);
  const suggested = problemSuggested(problem);
  const unlisted = problemUnlisted(problem);
  const pivotVia = problemPivotVia(problem);
  const hint = problemHint(problem);

  if (problem.code === "language_ambiguous") {
    const script = typeof problem.script === "string" ? problem.script : null;
    return (
      <Notice tone="info" title="Which language is this text in?">
        <p>
          {script
            ? `It is written in ${script} script, which more than one language uses, so the text alone cannot decide.`
            : problem.detail}
        </p>
        {candidates.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {candidates.map((code) => (
              <Button key={code} variant={code === suggested ? "primary" : "secondary"} onClick={() => onPickSource(code)}>
                {byCode[code] ? languageLabel(byCode[code]) : code}
                {code === suggested ? " (likely)" : ""}
              </Button>
            ))}
          </div>
        )}
        {unlisted.length > 0 && (
          <p className="mt-3 text-xs text-soft">Other languages that use this script are not supported yet: {unlisted.join(", ")}.</p>
        )}
      </Notice>
    );
  }

  const tone = pivotVia || problem.code === "model_not_downloaded" ? "warn" : "bad";
  return (
    <Notice tone={tone} title={problem.title}>
      <p>{problem.detail}</p>
      {pivotVia && (
        <div className="mt-3">
          <Button onClick={onAllowPivot}>Translate in two steps via {byCode[pivotVia]?.name ?? pivotVia}</Button>
          <p className="mt-1 text-xs">The text is translated twice, so quality can be lower.</p>
        </div>
      )}
      {hint && <p className="mt-2 font-mono text-xs">{hint}</p>}
      {tone === "bad" && problem.request_id && <p className="mt-2 text-xs">Request id: {problem.request_id}</p>}
    </Notice>
  );
}

export function TranslatePage({ languages, models, maxChars }: { languages: Language[]; models: ModelInfo[]; maxChars: number }) {
  const [source, setSource] = useState("auto");
  const [target, setTarget] = useState(
    () => languages.find((l) => l.code === "te" && l.can_be_target)?.code ?? languages.find((l) => l.can_be_target)?.code ?? "en",
  );
  const [modelId, setModelId] = useState("auto");
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<TranslateResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [copied, setCopied] = useState<"idle" | "copied" | "failed">("idle");
  const abortRef = useRef<AbortController | null>(null);

  const byCode = useMemo(() => indexByCode(languages), [languages]);
  const modelsById = useMemo(() => Object.fromEntries(models.map((m) => [m.id, m])), [models]);
  const sourceLanguages = useMemo(() => languages.filter((l) => l.can_be_source), [languages]);
  const targetLanguages = useMemo(() => languages.filter((l) => l.can_be_target), [languages]);
  const usableModels = useMemo(() => models.filter((m) => m.usable), [models]);
  const sourceLang = source === "auto" ? undefined : byCode[source];
  const targetLang = byCode[target];
  const busy = phase === "loading";
  const tooLong = text.length > maxChars;
  const sameLanguage = source !== "auto" && source === target;
  const canTranslate = text.trim().length > 0 && !busy && !tooLong && !sameLanguage;

  const run = useCallback(
    async (override: { source?: string; allowPivot?: boolean } = {}) => {
      const body = text.trim();
      if (!body) return;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setPhase("loading");
      setError(null);
      try {
        const response = await api.translate(
          {
            text: body,
            target_language: target,
            source_language: override.source ?? source,
            model_id: modelId === "auto" ? null : modelId,
            allow_pivot: override.allowPivot ?? false,
          },
          controller.signal,
        );
        if (abortRef.current !== controller) return; // a newer request replaced this one
        setResult(response);
        setPhase("done");
      } catch (caught) {
        if (abortRef.current !== controller) return;
        if (controller.signal.aborted) {
          setPhase("idle"); // the user cancelled
          return;
        }
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError({
                type: "about:blank",
                title: "Unexpected error",
                status: 0,
                detail: caught instanceof Error ? caught.message : "Something went wrong in the browser.",
                code: "client_error",
              }),
        );
        setResult(null);
        setPhase("error");
      }
    },
    [text, source, target, modelId],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setPhase("idle");
  }, []);

  const swap = useCallback(() => {
    const from = source === "auto" ? result?.source_language : source;
    if (!from) return;
    setSource(target);
    setTarget(from);
    if (result) {
      setText(result.translation);
      setResult(null);
      setPhase("idle");
    }
  }, [source, target, result]);

  const copy = useCallback(async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.translation);
      setCopied("copied");
    } catch {
      setCopied("failed");
    }
    window.setTimeout(() => setCopied("idle"), 2000);
  }, [result]);

  const download = useCallback(() => {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([result.translation], { type: "text/plain;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `translation-${result.source_language}-${result.target_language}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [result]);

  return (
    <div>
      <header className="mb-6">
        <h1 className="font-serif text-2xl font-semibold">Translate</h1>
        <p className="mt-1 text-sm text-soft">Choose the languages, paste your text, and see exactly which model produced the result and under which licence.</p>
      </header>

      <div className="grid items-start gap-4 md:grid-cols-[1fr_auto_1fr]">
        <section className="rounded-[10px] border border-rule bg-panel focus-within:border-accent focus-within:outline-2 focus-within:outline-accent">
          <div className="border-b border-rule px-4 py-3">
            <LanguageSelect id="source-language" label="From" value={source} onChange={setSource} languages={sourceLanguages} autoLabel="Detect language" />
          </div>
          <label htmlFor="source-text" className="sr-only">
            Text to translate
          </label>
          <textarea
            id="source-text"
            value={text}
            lang={sourceLang?.code}
            dir={sourceLang?.rtl ? "rtl" : "auto"}
            onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setText(event.target.value)}
            onKeyDown={(event: KeyboardEvent<HTMLTextAreaElement>) => {
              if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && canTranslate) {
                event.preventDefault();
                void run();
              }
            }}
            placeholder="Type or paste text. Press Ctrl+Enter to translate."
            className="block min-h-[14rem] w-full resize-y bg-transparent p-4 text-[1.05rem] leading-relaxed text-ink outline-none placeholder:text-soft"
          />
          <div className="flex items-center justify-between border-t border-rule px-4 py-2 text-xs text-soft">
            <span className={tooLong ? "font-semibold text-bad" : ""}>
              {formatCount(text.length)} / {formatCount(maxChars)} characters
            </span>
            <Button variant="ghost" onClick={() => setText("")} disabled={!text}>
              Clear
            </Button>
          </div>
        </section>

        <div className="flex items-center justify-center md:pt-12">
          <Button ariaLabel="Swap languages" title="Swap languages" onClick={swap} disabled={source === "auto" && !result}>
            ⇄
          </Button>
        </div>

        <section className="rounded-[10px] border border-rule bg-panel">
          <div className="border-b border-rule px-4 py-3">
            <LanguageSelect id="target-language" label="To" value={target} onChange={setTarget} languages={targetLanguages} />
          </div>
          <div
            aria-live="polite"
            lang={result?.target_language ?? targetLang?.code}
            dir={targetLang?.rtl ? "rtl" : "ltr"}
            className="min-h-[14rem] whitespace-pre-wrap p-4 text-[1.05rem] leading-relaxed"
          >
            {result ? result.translation : <span className="text-soft">Your translation appears here.</span>}
          </div>
          <div className="flex items-center gap-2 border-t border-rule px-4 py-2">
            <Button variant="ghost" onClick={() => void copy()} disabled={!result}>
              {copied === "copied" ? "Copied" : copied === "failed" ? "Copy failed" : "Copy"}
            </Button>
            <Button variant="ghost" onClick={download} disabled={!result}>
              Download .txt
            </Button>
          </div>
        </section>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label htmlFor="model-choice" className="text-sm text-soft">
            Model
          </label>
          <select
            id="model-choice"
            value={modelId}
            onChange={(event: ChangeEvent<HTMLSelectElement>) => setModelId(event.target.value)}
            className="rounded-md border border-rule bg-panel px-2.5 py-1.5 text-sm text-ink"
          >
            <option value="auto">Automatic (the router decides)</option>
            {usableModels.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
              </option>
            ))}
          </select>
        </div>
        <Button variant="primary" onClick={() => void run()} disabled={!canTranslate}>
          {busy ? "Translating…" : "Translate"}
        </Button>
        {busy && <Button onClick={cancel}>Cancel</Button>}
        {sameLanguage && <span className="text-sm text-warn">Choose two different languages.</span>}
      </div>
      <p className="sr-only" role="status">
        {busy ? "Translating" : ""}
      </p>
      {busy && <p className="mt-2 text-sm text-soft">The first request after starting the server loads the model, which can take a minute on a CPU.</p>}

      <div className="mt-6 space-y-4">
        {error && <ErrorPanel error={error} byCode={byCode} onPickSource={(code) => { setSource(code); void run({ source: code }); }} onAllowPivot={() => void run({ allowPivot: true })} />}

        {result && (
          <>
            <section aria-labelledby="route-title">
              <h2 id="route-title" className="mb-2 text-sm font-semibold text-soft">
                How this was translated
              </h2>
              <RouteLine
                legs={result.legs.map((leg) => ({ source: leg.source, target: leg.target, modelId: leg.model_id }))}
                languages={byCode}
                models={modelsById}
                pivotVia={result.pivot_via}
              />
            </section>

            {result.warnings.length > 0 && (
              <Notice tone="warn" title="Check this translation">
                <ul className="list-disc pl-5">
                  {result.warnings.map((w) => (
                    <li key={w.code}>
                      {describeWarning(w.code, w.detail)} {w.count > 1 ? `(${w.count} sentences)` : ""}
                    </li>
                  ))}
                </ul>
              </Notice>
            )}

            <details className="rounded-md border border-rule bg-panel px-4 py-3 text-sm">
              <summary className="cursor-pointer font-medium">Technical details</summary>
              <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-6 gap-y-1">
                <dt className="text-soft">Sentences</dt>
                <dd>{result.segments}</dd>
                <dt className="text-soft">Characters in / out</dt>
                <dd>
                  {formatCount(result.input_chars)} / {formatCount(result.output_chars)}
                </dd>
                {result.source_detection && (
                  <>
                    <dt className="text-soft">Language detection</dt>
                    <dd>
                      {result.source_detection.method === "unique_script"
                        ? `from the script (${result.source_detection.script})`
                        : `from ${result.source_detection.method ?? "the text"}`}
                    </dd>
                  </>
                )}
                {result.legs.map((leg, index) => (
                  <Fragment key={`${leg.model_id}-${index}`}>
                    <dt className="text-soft">
                      {leg.source} → {leg.target}
                    </dt>
                    <dd>
                      {leg.model_id} ({leg.model_revision ? leg.model_revision.slice(0, 8) : "revision not pinned"}) on {leg.device}; {leg.units} units in {leg.batches}{" "}
                      batches; token counts: {leg.token_counts}
                      {Object.keys(leg.split_units).length > 0 ? `; long sentences were split (${JSON.stringify(leg.split_units)})` : ""}
                    </dd>
                  </Fragment>
                ))}
                <dt className="text-soft">Time</dt>
                <dd>
                  {Object.entries(result.timings_ms)
                    .map(([key, value]) => `${key.replace("_ms", "").replace("_", " ")} ${formatMs(value)}`)
                    .join(" · ")}
                </dd>
              </dl>
              <p className="mt-3 text-xs text-soft">{result.note}</p>
            </details>
          </>
        )}
      </div>
    </div>
  );
}
