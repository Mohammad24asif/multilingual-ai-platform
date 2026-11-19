import { useEffect, useState } from "react";

export type Route = "translate" | "models" | "status";
const ROUTES: Route[] = ["translate", "models", "status"];

export function parseRoute(hash: string): Route {
  const name = hash.replace(/^#\/?/, "");
  return (ROUTES as string[]).includes(name) ? (name as Route) : "translate";
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
