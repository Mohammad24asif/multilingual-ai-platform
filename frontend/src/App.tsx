import { api } from "./api";
import { Button } from "./components/Button";
import { Notice } from "./components/Notice";
import { Shell } from "./components/Shell";
import { useAsync } from "./hooks/useAsync";
import { useHashRoute } from "./hooks/useHashRoute";
import { ModelsPage } from "./pages/ModelsPage";
import { StatusPage } from "./pages/StatusPage";
import { TranslatePage } from "./pages/TranslatePage";

export function App() {
  const route = useHashRoute();
  const data = useAsync(async () => {
    const [languages, models, system, readiness] = await Promise.all([
      api.languages(),
      api.models(),
      api.system().catch(() => null),
      api.readiness().catch(() => null),
    ]);
    return { languages, models, system, readiness };
  }, []);

  const loaded = data.data;
  return (
    <Shell route={route} readiness={loaded?.readiness ?? null}>
      {data.status === "loading" && !loaded && <p className="text-soft">Loading…</p>}
      {data.status === "error" && (
        <div className="space-y-3">
          <Notice tone="bad" title="The app could not load from the server">
            <p>{data.error?.message}</p>
          </Notice>
          <Button onClick={data.reload}>Try again</Button>
        </div>
      )}
      {loaded && route === "translate" && (
        <TranslatePage languages={loaded.languages} models={loaded.models} maxChars={loaded.system?.policy.max_input_chars ?? 20_000} />
      )}
      {loaded && route === "models" && <ModelsPage languages={loaded.languages} models={loaded.models} />}
      {route === "status" && <StatusPage />}
    </Shell>
  );
}
