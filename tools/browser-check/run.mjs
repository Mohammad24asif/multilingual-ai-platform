// Builds the bundle, starts three stand-in servers (default, pivot, slow), runs the browser scenarios and stops the servers.
//   node tools/browser-check/run.mjs
// Environment: PYTHON (default "python", for example "uv run --project backend python"), PLAYWRIGHT_DIR, CHROMIUM_PATH.
import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const build = spawnSync(process.execPath, [path.join(here, "build.mjs")], { stdio: "inherit" });
if (build.status !== 0) process.exit(build.status ?? 1);

const python = (process.env.PYTHON ?? "python").split(" ");
const servers = [["default", 8101], ["pivot", 8102], ["slow", 8103]].map(([scenario, port]) =>
  spawn(python[0], [...python.slice(1), path.join(here, "server.py"), "--port", String(port), "--scenario", scenario], { stdio: "ignore" }),
);
const stop = () => servers.forEach((s) => s.kill());
process.on("exit", stop);

async function waitFor(port) {
  for (let i = 0; i < 60; i++) {
    try {
      if ((await fetch(`http://127.0.0.1:${port}/api/v1/health/live`)).ok) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`stand-in server on port ${port} did not start (is PYTHON correct?)`);
}
await Promise.all([8101, 8102, 8103].map(waitFor));
await import("./scenarios.mjs"); // exits the process with the right status when done
