import { useCallback, useEffect, useState } from "react";

export interface AsyncState<T> {
  status: "loading" | "done" | "error";
  data?: T;
  error?: Error;
}

export function useAsync<T>(load: () => Promise<T>, deps: readonly unknown[] = []): AsyncState<T> & { reload: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setState((previous) => ({ ...previous, status: "loading" }));
    load().then(
      (data) => {
        if (!cancelled) setState({ status: "done", data });
      },
      (error: unknown) => {
        if (!cancelled) setState({ status: "error", error: error instanceof Error ? error : new Error(String(error)) });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [...deps, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
