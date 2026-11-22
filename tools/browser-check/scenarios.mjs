import { createRequire } from "node:module";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
// Playwright is an optional dev tool: `npm install --no-save playwright && npx playwright install chromium` in frontend/.
const require = createRequire(path.join(process.env.PLAYWRIGHT_DIR ?? path.join(here, "..", "..", "frontend", "node_modules"), "/"));
const { chromium } = require("playwright");
const SHOTS = path.join(here, "shots");
fs.mkdirSync(SHOTS, { recursive: true });

const browser = await chromium.launch({ args: ["--no-sandbox"], ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
const results = [];
const consoleProblems = [];

async function scenario(name, baseUrl, body, { viewport = { width: 1280, height: 900 }, colorScheme = "light" } = {}) {
  const context = await browser.newContext({ viewport, colorScheme });
  const page = await context.newPage();
  page.on("pageerror", (e) => consoleProblems.push(`[${name}] pageerror: ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error" && !/status of (4|5)\d\d|Failed to load resource/.test(m.text())) consoleProblems.push(`[${name}] console: ${m.text()}`); });
  try {
    await page.goto(baseUrl);
    await page.getByRole("heading", { name: "Translate", level: 1 }).waitFor({ timeout: 8000 });
    await body(page, baseUrl);
    results.push([name, true, ""]);
  } catch (error) {
    results.push([name, false, String(error.message).split("\n")[0]]);
    await page.screenshot({ path: `${SHOTS}/FAIL-${name.replace(/\W+/g, "_")}.png` }).catch(() => {});
  } finally {
    await context.close();
  }
}
const translateBtn = (page) => page.getByRole("button", { name: "Translate", exact: true });
const D = "http://127.0.0.1:8101", P = "http://127.0.0.1:8102", S = "http://127.0.0.1:8103";

await scenario("accessible controls exist and Translate starts disabled", D, async (page) => {
  await page.getByLabel("Text to translate").waitFor();
  for (const label of ["From", "To", "Model"]) await page.getByLabel(label, { exact: true }).waitFor();
  await page.getByRole("link", { name: "Models and languages" }).waitFor();
  assert.equal(await translateBtn(page).isDisabled(), true);
  assert.ok(await page.getByText("Your translation appears here.").isVisible());
});

await scenario("English to Telugu via keyboard shortcut; route line, licence and details", D, async (page) => {
  await page.locator("#source-language").selectOption("en");
  await page.locator("#target-language").selectOption("te");
  await page.getByLabel("Text to translate").fill("Hello there friend. How are you today?");
  await page.getByLabel("Text to translate").press("Control+Enter");
  await page.getByText("తెలుగు పాఠం").first().waitFor({ timeout: 8000 });
  const route = page.getByRole("list", { name: "Translation route" });
  const routeText = await route.innerText();
  assert.match(routeText, /NLLB-200 distilled \(600M\)/);
  assert.match(routeText, /CC-BY-NC-4\.0 · research only/);
  assert.equal(await page.locator('[aria-live="polite"]').getAttribute("lang"), "te");
  await page.getByText("Technical details").click();
  const details = await page.locator("details").innerText();
  assert.match(details, /nllb-200-distilled-600m/);
  assert.match(details, /revision not pinned/);
  assert.match(details, /No confidence score/);
  await page.screenshot({ path: `${SHOTS}/translate-light.png` });
});

await scenario("auto-detects Telugu from script", D, async (page) => {
  await page.locator("#target-language").selectOption("en");
  await page.getByLabel("Text to translate").fill("నమస్కారం, మీరు ఎలా ఉన్నారు?");
  await translateBtn(page).click();
  await page.getByText("translated text").first().waitFor({ timeout: 8000 });
  await page.getByText("Technical details").click();
  assert.match(await page.locator("details").innerText(), /from the script \(Telugu\)/);
});

await scenario("ambiguous Devanagari asks which language, then continues", D, async (page) => {
  await page.getByLabel("Text to translate").fill("नमस्ते, आप कैसे हैं?");
  await page.locator("#target-language").selectOption("en");
  await translateBtn(page).click();
  await page.getByText("Which language is this text in?").waitFor({ timeout: 8000 });
  await page.screenshot({ path: `${SHOTS}/ambiguous.png` });
  const hindi = page.getByRole("button", { name: "हिन्दी · Hindi" });
  assert.ok(await page.getByRole("button", { name: "मराठी · Marathi" }).isVisible());
  await hindi.click();
  await page.getByText("translated text").first().waitFor({ timeout: 8000 });
  assert.equal(await page.locator("#source-language").inputValue(), "hi");
});

await scenario("same language disables Translate with a message", D, async (page) => {
  await page.locator("#source-language").selectOption("en");
  await page.locator("#target-language").selectOption("en");
  await page.getByLabel("Text to translate").fill("Hello there friend.");
  assert.ok(await page.getByText("Choose two different languages.").isVisible());
  assert.equal(await translateBtn(page).isDisabled(), true);
});

await scenario("swap moves the result into the input and flips languages", D, async (page) => {
  await page.locator("#source-language").selectOption("en");
  await page.locator("#target-language").selectOption("te");
  await page.getByLabel("Text to translate").fill("Hello there friend.");
  await translateBtn(page).click();
  await page.getByText("తెలుగు పాఠం").first().waitFor({ timeout: 8000 });
  await page.getByRole("button", { name: "Swap languages" }).click();
  assert.equal(await page.locator("#source-language").inputValue(), "te");
  assert.equal(await page.locator("#target-language").inputValue(), "en");
  assert.match(await page.getByLabel("Text to translate").inputValue(), /తెలుగు పాఠం/);
  assert.ok(await page.getByText("Your translation appears here.").isVisible());
});

await scenario("models page shows licences, blockers and evidence", D, async (page) => {
  await page.getByRole("link", { name: "Models and languages" }).click();
  await page.getByRole("heading", { name: "Models and languages", level: 1 }).waitFor();
  const text = await page.locator("main").innerText();
  for (const expected of ["Research use only", "Blocked", "Switched off in the settings.", "IndicTrans2 English to Indic (distilled 200M)", "Language codes verified against the tokenizer: not yet"]) {
    assert.ok(text.includes(expected), `missing: ${expected}`);
  }
  assert.equal(await page.locator("table tbody tr").count(), 11);
  await page.screenshot({ path: `${SHOTS}/models-light.png`, fullPage: true });
});

await scenario("status page explains readiness and hardware", D, async (page) => {
  await page.getByRole("link", { name: "Status" }).click();
  await page.getByText("Work queue").waitFor({ timeout: 8000 });
  const text = await page.locator("main").innerText();
  assert.ok(text.includes("Ready to translate"));
  assert.ok(text.includes("CPU (no GPU needed)"));
  assert.ok(text.includes("Work queue"));
});

await scenario("dark mode toggles and is remembered", D, async (page) => {
  await page.getByRole("button", { name: "Dark mode" }).click();
  assert.equal(await page.evaluate(() => document.documentElement.classList.contains("dark")), true);
  assert.equal(await page.evaluate(() => localStorage.getItem("theme")), "dark");
  await page.getByLabel("Text to translate").fill("Hello there friend.");
  await page.screenshot({ path: `${SHOTS}/translate-dark.png` });
});

await scenario("pivot is offered, never automatic, and disclosed", P, async (page) => {
  await page.locator("#source-language").selectOption("te");
  await page.locator("#target-language").selectOption("hi");
  await page.getByLabel("Text to translate").fill("ఇది ఒక పరీక్ష. ఇది రెండవది.");
  await translateBtn(page).click();
  const offer = page.getByRole("button", { name: /Translate in two steps via English/ });
  await offer.waitFor({ timeout: 8000 });
  assert.ok(await page.getByText("No suitable model for this language pair").isVisible());
  await offer.click();
  await page.getByText(/Two-step translation through English/).waitFor({ timeout: 8000 });
  const rows = await page.getByRole("list", { name: "Translation route" }).locator("li").allInnerTexts();
  assert.equal(rows.length, 2, "one row per step");
  assert.match(rows[0], /Step 1/); assert.match(rows[1], /Step 2/);
  assert.match(rows[0], /mBART-50/); assert.match(rows[1], /NLLB-200/);
  await page.screenshot({ path: `${SHOTS}/pivot.png` });
});

await scenario("cancel stops a slow translation without showing a result", S, async (page) => {
  await page.locator("#source-language").selectOption("en");
  await page.locator("#target-language").selectOption("te");
  await page.getByLabel("Text to translate").fill(Array.from({ length: 12 }, (_, i) => `Sentence number ${i} is here.`).join(" "));
  await page.getByRole("button", { name: "Translating…" }).waitFor({ state: "attached", timeout: 1 }).catch(() => {});
  await page.getByRole("button", { name: "Translate", exact: true }).click();
  await page.getByRole("button", { name: "Cancel" }).waitFor({ timeout: 3000 });
  await page.getByRole("button", { name: "Cancel" }).click();
  await page.getByRole("button", { name: "Translate", exact: true }).waitFor({ timeout: 3000 });
  await page.waitForTimeout(800);
  assert.ok(await page.getByText("Your translation appears here.").isVisible());
});

await scenario("unreachable server gives a friendly error", D, async (page) => {
  await page.route("**/api/v1/translate", (route) => route.abort());
  await page.locator("#source-language").selectOption("en");
  await page.locator("#target-language").selectOption("te");
  await page.getByLabel("Text to translate").fill("Hello there friend.");
  await translateBtn(page).click();
  await page.getByText("Cannot reach the server").waitFor({ timeout: 8000 });
  assert.ok((await page.getByRole("alert").innerText()).includes("uv run uvicorn"));
});

await scenario("narrow phone layout stacks the panes without sideways scrolling", D, async (page) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByLabel("Text to translate").fill("Hello there friend.");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert.ok(overflow <= 1, `page scrolls sideways by ${overflow}px`);
  await page.screenshot({ path: `${SHOTS}/translate-phone.png`, fullPage: true });
}, { viewport: { width: 390, height: 844 } });

await browser.close();
let failed = 0;
for (const [name, ok, why] of results) { console.log(ok ? "  ok  " : "  FAIL", name, ok ? "" : `\n        ${why}`); if (!ok) failed++; }
if (consoleProblems.length) { console.log("\nbrowser console problems:"); consoleProblems.forEach((p) => console.log("  ", p)); failed++; }
console.log(`\n${results.length - results.filter((r) => !r[1]).length}/${results.length} browser scenarios passed`);
process.exit(failed ? 1 : 0);
