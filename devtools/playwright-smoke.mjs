import { appendFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const requireFromCwd = createRequire(path.join(process.cwd(), "package.json"));
const { chromium, request: playwrightRequest } = requireFromCwd("playwright");

const WEB_BASE_URL = process.env.WEB_BASE_URL ?? "http://localhost:5173";
const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
/** First ingest loads the embedding model; cold CPU runs often exceed 20s. */
const INGEST_TIMEOUT_MS = Number(process.env.INGEST_TIMEOUT_MS ?? 120000);
/** First UI query also embeds the question; allow same order of magnitude as ingest on cold start. */
const QUERY_TIMEOUT_MS = Number(process.env.QUERY_TIMEOUT_MS ?? 120000);
const SKIP_INGEST = process.env.SMOKE_SKIP_INGEST === "1" || process.env.SMOKE_SKIP_INGEST === "true";
const ERROR_DB_PATH = path.join(rootDir, "devtools", "error-tracking-db.md");

function nowIso() {
  return new Date().toISOString();
}

function todayStamp() {
  return new Date().toISOString().slice(0, 10);
}

async function runSmoke() {
  const checks = [];
  let browser;
  let req;

  try {
    req = await playwrightRequest.newContext();

    // 1) CORS preflight
    const preflight = await req.fetch(`${API_BASE_URL}/health`, {
      method: "OPTIONS",
      headers: {
        Origin: WEB_BASE_URL,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "content-type",
      },
      timeout: 10000,
    });
    const acao = preflight.headers()["access-control-allow-origin"] ?? "";
    checks.push({
      name: "CORS preflight",
      ok: preflight.status() === 200 && acao === WEB_BASE_URL,
      detail: `status=${preflight.status()} acao=${acao || "<missing>"}`,
    });

    const health = await req.fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      timeout: 15000,
    });
    const healthBody = await health.text();
    checks.push({
      name: "API health (GET)",
      ok: health.ok(),
      detail: `status=${health.status()} body=${healthBody.slice(0, 200)}`,
    });
    if (!health.ok()) {
      throw new Error(
        `API not healthy at ${API_BASE_URL}/health (status ${health.status()}). ` +
          "Start the stack: docker compose up -d",
      );
    }

    if (SKIP_INGEST) {
      checks.push({
        name: "Seed ingest",
        ok: true,
        detail: "skipped (SMOKE_SKIP_INGEST=1)",
      });
    } else {
      const ingest = await req.fetch(`${API_BASE_URL}/ingest/path`, {
        method: "POST",
        data: { path: "/data/sources", recursive: true },
        timeout: INGEST_TIMEOUT_MS,
      });
      checks.push({
        name: "Seed ingest",
        ok: ingest.ok(),
        detail: `status=${ingest.status()} timeout_ms=${INGEST_TIMEOUT_MS}`,
      });
      if (!ingest.ok()) {
        const body = await ingest.text();
        throw new Error(
          `Ingest failed: status=${ingest.status()} ${body.slice(0, 300)}. ` +
            "If this was a timeout, increase INGEST_TIMEOUT_MS or run ingest once manually after model download.",
        );
      }
    }

    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // 2) Dashboard load
    await page.goto(WEB_BASE_URL, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.getByRole("heading", { name: "VECTORDB-BRAIN" }).waitFor({ timeout: 15000 });
    const statusBadge = page.locator(".badge", { hasText: "API:" }).first();
    await statusBadge.waitFor({ timeout: 10000 });
    checks.push({
      name: "Dashboard load",
      ok: true,
      detail: "Heading and status badge rendered.",
    });

    // 3) Warm query API (same embedder path as UI) so the browser step is not the first cold embed.
    const warmQuery = await req.post(`${API_BASE_URL}/query`, {
      data: { query: "sample-note", limit: 5 },
      timeout: QUERY_TIMEOUT_MS,
    });
    checks.push({
      name: "Query warm-up (API)",
      ok: warmQuery.ok(),
      detail: `status=${warmQuery.status()} timeout_ms=${QUERY_TIMEOUT_MS}`,
    });
    if (!warmQuery.ok()) {
      const body = await warmQuery.text();
      throw new Error(
        `Query warm-up failed: status=${warmQuery.status()} ${body.slice(0, 300)}. ` +
          "Check Qdrant has vectors after ingest (corpus summary / ingest logs).",
      );
    }

    // 4) Query run from UI — wait for POST /query, then for result cards (or surface API error).
    await page.getByLabel("Query").fill("sample-note");
    const queryResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/query") &&
        response.request().method() === "POST" &&
        response.status() !== 0,
      { timeout: QUERY_TIMEOUT_MS },
    );
    await page.getByRole("button", { name: "Run query" }).click();
    const queryResponse = await queryResponsePromise;
    const queryOk = queryResponse.ok();
    let queryBody = "";
    try {
      queryBody = await queryResponse.text();
    } catch {
      queryBody = "";
    }
    await page
      .locator(".result-card, .panel.error, .results .small")
      .first()
      .waitFor({ timeout: 15000 });
    const resultCount = await page.locator(".result-card").count();
    const errorVisible = (await page.locator(".panel.error").count()) > 0;
    checks.push({
      name: "Query run (UI)",
      ok: queryOk && resultCount > 0 && !errorVisible,
      detail: `http=${queryResponse.status()} result_cards=${resultCount} error_panel=${errorVisible} body=${queryBody.slice(0, 120)}`,
    });
    if (!queryOk || resultCount === 0) {
      throw new Error(
        `UI query did not produce result cards (http=${queryResponse.status()}, cards=${resultCount}). ` +
          `Body: ${queryBody.slice(0, 300)}`,
      );
    }

    const allOk = checks.every((c) => c.ok);
    return {
      ok: allOk,
      checks,
      timestamp: nowIso(),
      webBaseUrl: WEB_BASE_URL,
      apiBaseUrl: API_BASE_URL,
      error: null,
    };
  } catch (error) {
    return {
      ok: false,
      checks,
      timestamp: nowIso(),
      webBaseUrl: WEB_BASE_URL,
      apiBaseUrl: API_BASE_URL,
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    if (browser) {
      await browser.close();
    }
    if (req) {
      await req.dispose();
    }
  }
}

function renderEntry(result) {
  const incidentId = `VDB-SMOKE-${todayStamp()}-${result.ok ? "PASS" : "FAIL"}`;
  const lines = [];
  lines.push("");
  lines.push(`## Incident ${incidentId}`);
  lines.push("");
  lines.push(`- Timestamp: \`${result.timestamp}\``);
  lines.push(`- Type: \`playwright-smoke\``);
  lines.push(`- Status: \`${result.ok ? "PASS" : "FAIL"}\``);
  lines.push(`- Web URL: \`${result.webBaseUrl}\``);
  lines.push(`- API URL: \`${result.apiBaseUrl}\``);
  if (result.error) {
    lines.push(`- Error: \`${result.error}\``);
  }
  lines.push(`- Checks:`);
  for (const check of result.checks) {
    lines.push(`  - ${check.ok ? "PASS" : "FAIL"} | ${check.name} | ${check.detail}`);
  }
  lines.push("");
  return lines.join("\n");
}

async function main() {
  const result = await runSmoke();
  const entry = renderEntry(result);
  await appendFile(ERROR_DB_PATH, `${entry}\n`, "utf-8");

  for (const check of result.checks) {
    // eslint-disable-next-line no-console
    console.log(`${check.ok ? "PASS" : "FAIL"} | ${check.name} | ${check.detail}`);
  }
  if (result.error) {
    // eslint-disable-next-line no-console
    console.error(`ERROR: ${result.error}`);
  }
  // eslint-disable-next-line no-console
  console.log(`Entry appended to ${ERROR_DB_PATH}`);
  process.exit(result.ok ? 0 : 1);
}

await main();
