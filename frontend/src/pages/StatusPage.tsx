import { api } from "../api";
import { Button } from "../components/Button";
import { Notice } from "../components/Notice";
import { useAsync } from "../hooks/useAsync";
import { formatCount, formatMb } from "../lib/format";

export function StatusPage() {
  const readiness = useAsync(() => api.readiness(), []);
  const system = useAsync(() => api.system(), []);
  const refresh = () => {
    readiness.reload();
    system.reload();
  };
  const ready = readiness.data;
  const info = system.data;
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-serif text-2xl font-semibold">Status</h1>
          <p className="mt-1 text-sm text-soft">Whether the server is up is separate from whether a model is ready to translate.</p>
        </div>
        <Button onClick={refresh}>Refresh</Button>
      </header>

      {readiness.status === "error" && <Notice tone="bad" title="Cannot reach the server">{readiness.error?.message}</Notice>}
      {ready && (
        <Notice tone={ready.ready ? "ok" : "warn"} title={ready.ready ? "Ready to translate" : "Not ready to translate yet"}>
          {ready.problems.length > 0 && (
            <ul className="mt-1 list-disc pl-5">
              {ready.problems.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          )}
          <p className="mt-1">
            Usable models: {ready.usable_models.length > 0 ? ready.usable_models.join(", ") : "none"}. In memory: {ready.loaded_models.length > 0 ? ready.loaded_models.join(", ") : "none"}.
          </p>
        </Notice>
      )}

      {info && (
        <div className="grid gap-4 lg:grid-cols-3">
          <section className="rounded-[10px] border border-rule bg-panel p-4">
            <h2 className="mb-2 font-semibold">This computer</h2>
            <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1 text-sm">
              <dt className="text-soft">Device</dt>
              <dd>{info.device === "cpu" ? "CPU (no GPU needed)" : info.device}</dd>
              <dt className="text-soft">CPU threads</dt>
              <dd>{info.hardware.cpu_count_logical ?? "unknown"}</dd>
              <dt className="text-soft">Memory</dt>
              <dd>
                {formatMb(info.hardware.ram_available_mb)} free of {formatMb(info.hardware.ram_total_mb)}
              </dd>
              <dt className="text-soft">PyTorch</dt>
              <dd>{info.hardware.torch.installed ? info.hardware.torch.version : "not installed"}</dd>
              <dt className="text-soft">Python</dt>
              <dd>{info.hardware.python}</dd>
            </dl>
          </section>
          <section className="rounded-[10px] border border-rule bg-panel p-4">
            <h2 className="mb-2 font-semibold">Work queue</h2>
            <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1 text-sm">
              <dt className="text-soft">Waiting</dt>
              <dd>
                {info.queue.depth} of {info.queue.capacity}
              </dd>
              <dt className="text-soft">Translating now</dt>
              <dd>{info.queue.running ? "yes" : "no"}</dd>
              <dt className="text-soft">Finished</dt>
              <dd>{formatCount(info.queue.completed)}</dd>
              <dt className="text-soft">Failed</dt>
              <dd>{formatCount(info.queue.failed)}</dd>
              <dt className="text-soft">Turned away (busy)</dt>
              <dd>{formatCount(info.queue.rejected)}</dd>
            </dl>
          </section>
          <section className="rounded-[10px] border border-rule bg-panel p-4">
            <h2 className="mb-2 font-semibold">Policy</h2>
            <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1 text-sm">
              <dt className="text-soft">Licence mode</dt>
              <dd>{info.policy.licence_mode}</dd>
              <dt className="text-soft">Memory budget</dt>
              <dd>{info.policy.ram_budget_mb ? formatMb(info.policy.ram_budget_mb) : "not set"}</dd>
              <dt className="text-soft">Models in memory</dt>
              <dd>at most {info.policy.max_loaded_models}</dd>
              <dt className="text-soft">Downloads</dt>
              <dd>{info.policy.downloads_allowed ? "allowed" : "only by you, with a script"}</dd>
              <dt className="text-soft">Time limit</dt>
              <dd>{info.policy.inference_timeout_s} s per request</dd>
            </dl>
          </section>
        </div>
      )}
    </div>
  );
}
