// Bundles the real frontend with esbuild and compiles its Tailwind v4 CSS with Tailwind's own compiler.
// It is a lightweight stand-in for `vite build` so the UI can be exercised in a browser against the Python core.
// Needs `npm install` to have been run in frontend/ (esbuild and tailwindcss come with Vite and Tailwind).
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(process.env.FRONTEND_DIR ?? path.join(here, "..", "..", "frontend"));
const MODULES = path.resolve(process.env.TOOLS_NODE_MODULES ?? path.join(FRONTEND, "node_modules"));
const SRC = path.resolve(process.env.FRONTEND_SRC ?? path.join(FRONTEND, "src"));
const OUT = path.join(here, "dist");
const require = createRequire(path.join(MODULES, "/"));
const esbuild = require("esbuild");
const { compile } = require("tailwindcss");
const TW = path.join(MODULES, "tailwindcss");
fs.mkdirSync(OUT, { recursive: true });

await esbuild.build({
  entryPoints: [path.join(SRC, "main.tsx")], bundle: true, format: "esm", outfile: path.join(OUT, "app.js"),
  jsx: "automatic", loader: { ".css": "empty" }, define: { "process.env.NODE_ENV": '"development"' }, logLevel: "warning",
});

const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const candidates = new Set();
for (const file of walk(SRC).filter((f) => /\.(tsx?|css)$/.test(f) && !/\.test\./.test(f))) {
  for (const token of fs.readFileSync(file, "utf8").match(/[^\s"'`{}<>=,;]+/g) ?? []) candidates.add(token);
}
const loadStylesheet = async (id, base) => {
  const abs = id === "tailwindcss" ? path.join(TW, "index.css") : id.startsWith("tailwindcss/") ? path.join(TW, id.slice("tailwindcss/".length)) : path.resolve(base, id);
  return { path: abs, base: path.dirname(abs), content: fs.readFileSync(abs, "utf8") };
};
const compiler = await compile(fs.readFileSync(path.join(SRC, "index.css"), "utf8"), { base: SRC, loadStylesheet });
fs.writeFileSync(path.join(OUT, "app.css"), compiler.build([...candidates]));
fs.writeFileSync(path.join(OUT, "index.html"), `<!doctype html><html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/><title>Multilingual AI Platform</title><link rel="stylesheet" href="/app.css"/></head><body><div id="root"></div><script type="module" src="/app.js"></script></body></html>`);
console.log("built", path.join(OUT, "app.js"), fs.statSync(path.join(OUT, "app.js")).size, "bytes");
