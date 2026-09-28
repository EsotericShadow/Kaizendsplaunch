// Chromium launch + composition page helpers (playwright-core, no bundled browser download).

import fs from "node:fs";
import crypto from "node:crypto";
import { chromium } from "playwright-core";

// playwright-core 1.56.1 drives Chromium revision 1194 (141.0.7390.37), which is what is
// installed under /opt/pw-browsers. Override with CHROMIUM_PATH / --browser-path.
const CANDIDATES = {
  chrome: [
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/opt/pw-browsers/chromium",
  ],
  shell: ["/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell"],
};

export function findChromium(kind = "chrome", explicit = process.env.CHROMIUM_PATH) {
  if (explicit) {
    if (!fs.existsSync(explicit)) throw new Error(`Chromium not found at ${explicit}`);
    return explicit;
  }
  for (const p of CANDIDATES[kind] || []) if (fs.existsSync(p)) return p;
  throw new Error(`No Chromium (${kind}) found. Set CHROMIUM_PATH. Looked in: ${(CANDIDATES[kind] || []).join(", ")}`);
}

// Flags chosen for repeatable pixels and no background throttling.
export const CHROME_ARGS = [
  "--force-color-profile=srgb", // no monitor/ICC dependent colour management
  "--disable-lcd-text", // greyscale AA text; subpixel colour fringes look bad in video
  "--font-render-hinting=none", // same glyph shapes as macOS-style rendering, no hinting jitter
  "--hide-scrollbars",
  "--mute-audio",
  "--disable-background-timer-throttling",
  "--disable-renderer-backgrounding",
  "--disable-backgrounding-occluded-windows",
  "--disable-features=Translate,MediaRouter,OptimizationHints,CalculateNativeWinOcclusion,PaintHolding",
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-extensions",
  "--disable-component-update",
  "--disable-sync",
  "--disable-dev-shm-usage",
];

export async function launchBrowser({ kind = "chrome", executablePath, extraArgs = [], gpu = false } = {}) {
  const exe = executablePath || findChromium(kind);
  // Chromium ignores unknown switches; this one lets us find the browser PID in /proc so a hung
  // browser can be SIGKILLed (playwright's Browser object does not expose its process).
  const marker = `--kaizen-render-id=${crypto.randomUUID()}`;
  const args = [...CHROME_ARGS, ...extraArgs, marker];
  if (!gpu) args.push("--disable-gpu");
  const browser = await chromium.launch({
    executablePath: exe,
    headless: true,
    args,
    timeout: 60_000,
  });
  browser.__pid = findPidByArg(marker);
  browser.__marker = marker;
  return browser;
}

function findPidByArg(marker) {
  try {
    for (const d of fs.readdirSync("/proc")) {
      if (!/^\d+$/.test(d)) continue;
      let cmd;
      try {
        cmd = fs.readFileSync(`/proc/${d}/cmdline`, "utf8");
      } catch {
        continue;
      }
      if (cmd.includes(marker) && !cmd.includes("--type=")) return Number(d);
    }
  } catch {}
  return null; // not Linux, or not found: kill fallback unavailable
}

/** Close a browser; SIGKILL it if close() hangs or the connection is already gone. */
export async function closeBrowser(browser, timeoutMs = 10_000) {
  try {
    await withTimeout(browser.close(), timeoutMs, "browser.close");
  } catch {
    killBrowser(browser);
  }
}

export function killBrowser(browser) {
  if (!browser.__pid) return;
  try {
    // Only if the PID still belongs to this browser (PIDs are reused after a process exits).
    const cmd = fs.readFileSync(`/proc/${browser.__pid}/cmdline`, "utf8");
    if (cmd.includes(browser.__marker)) process.kill(browser.__pid, "SIGKILL");
  } catch {}
}

/** Promise with a timeout and a readable label. */
export function withTimeout(promise, ms, label) {
  let timer;
  const t = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`Timeout after ${ms} ms: ${label}`)), ms);
  });
  return Promise.race([promise, t]).finally(() => clearTimeout(timer));
}

/**
 * Open a composition page and wait until it is ready to seek.
 * Returns { context, page, cdp, meta, errors } where errors collects page errors/failed requests.
 */
export async function openComposition(browser, {
  url,
  viewport = { width: 1920, height: 1080 },
  scale = 1,
  allowNetwork = false,
  origin,
  seed = 1,
  readyTimeoutMs = 180_000,
  log = () => {},
  tag = "",
}) {
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: scale,
    reducedMotion: "no-preference",
    colorScheme: "dark",
    serviceWorkers: "block",
  });
  const errors = [];
  // Same Math.random sequence in every worker page, before any page script runs.
  await context.addInitScript((s) => {
    let a = s >>> 0;
    Math.random = function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }, seed);
  if (!allowNetwork) {
    await context.route("**/*", (route) => {
      const u = route.request().url();
      if (u.startsWith(origin) || u.startsWith("data:") || u.startsWith("blob:")) return route.continue();
      errors.push(`blocked external request: ${u}`);
      log(`${tag} blocked external request ${u} (use --allow-network to permit)`);
      return route.abort("blockedbyclient");
    });
  }
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") log(`${tag} console.${m.type()}: ${m.text()}`);
  });
  page.on("response", (r) => {
    if (r.status() >= 400 && !r.url().endsWith("/favicon.ico")) errors.push(`HTTP ${r.status()} ${r.url()}`);
  });
  page.on("requestfailed", (r) => {
    const f = r.failure();
    if (f && f.errorText !== "net::ERR_BLOCKED_BY_CLIENT") errors.push(`request failed: ${r.url()} ${f.errorText}`);
  });

  await withTimeout(page.goto(url, { waitUntil: "load", timeout: 60_000 }), 70_000, `load ${url}`);
  const fatal = (msg) => {
    const e = new Error(errors.length ? `${msg}\n  ${errors.join("\n  ")}` : msg);
    e.fatal = true; // deterministic problem in the composition: retrying will not help
    return e;
  };
  try {
    await withTimeout(
      page.waitForFunction(() => window.__composition && typeof window.__composition.seek === "function", null, {
        timeout: readyTimeoutMs,
      }),
      readyTimeoutMs + 5000,
      "window.__composition to appear",
    );
  } catch (e) {
    if (errors.length) throw fatal(`window.__composition never appeared (page errors below)`);
    throw e;
  }
  // Optional readiness promise (the runtime provides one; hand-written compositions may not).
  try {
    await withTimeout(
      page.evaluate(async () => {
        const c = window.__composition;
        if (c.ready && typeof c.ready.then === "function") await c.ready;
      }),
      readyTimeoutMs,
      "composition ready (fonts, images, sequences)",
    );
  } catch (e) {
    // Timeouts and crashes may be load related and are retried; a rejected ready() is not.
    if (/^Timeout after|closed|crash/i.test(e.message)) throw e;
    throw fatal(`Composition setup failed: ${e.message.replace(/^page\.evaluate: /, "")}`);
  }
  const meta = await page.evaluate(() => {
    const c = window.__composition;
    return { width: c.width, height: c.height, fps: c.fps, duration: c.duration };
  });
  for (const k of ["width", "height", "fps", "duration"]) {
    if (!(meta[k] > 0)) throw fatal(`window.__composition.${k} must be a positive number (got ${meta[k]})`);
  }
  const cdp = await context.newCDPSession(page);
  return { context, page, cdp, meta, errors };
}

/** Seek, then capture the viewport. Returns a Buffer (jpeg or png). */
// For scale != 1 pass clip = { x: 0, y: 0, width, height, scale }: without a clip,
// Page.captureScreenshot returns CSS-pixel size even when deviceScaleFactor is 2 or 0.5.
// With clip.scale Chromium re-rasters at that scale (sharp text at 4K, not an upscale).
export async function seekAndCapture(page, cdp, t, { format = "jpeg", quality = 95, timeoutMs = 30_000, clip = null } = {}) {
  await withTimeout(page.evaluate((tt) => window.__composition.seek(tt), t), timeoutMs, `seek(${t})`);
  const params = { format, captureBeyondViewport: false, fromSurface: true, optimizeForSpeed: true };
  if (format === "jpeg" || format === "webp") params.quality = quality;
  if (clip) params.clip = clip;
  const { data } = await withTimeout(cdp.send("Page.captureScreenshot", params), timeoutMs, `capture at t=${t}`);
  return Buffer.from(data, "base64");
}
