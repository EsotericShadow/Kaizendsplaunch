#!/usr/bin/env node
// Download Google Fonts (CSS2 API) into assets/fonts/ for offline, deterministic renders.
//
//   node tools/fetch-fonts.mjs "Fraunces:ital,wght@0,400;0,600;0,700;0,900;1,400;1,600;1,700;1,900" \
//                              "Inter:wght@400;600;700" [--subsets latin,latin-ext] [--out assets/fonts]
//
// Writes assets/fonts/<family>/<file>.woff2 and assets/fonts/<family>.css with local URLs, so a
// composition links /assets/fonts/fraunces.css. Renders block network access, so fonts must be
// local. The npm @fontsource packages (already in package.json) are the other local source; this
// script exists for families or axes that fontsource does not ship. All Google Fonts used here
// are SIL OFL 1.1: keep the licence with the files if you commit them anywhere.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import { parseArgs } from "node:util";
import { fileURLToPath } from "node:url";

// Node's fetch only honours HTTPS_PROXY when NODE_USE_ENV_PROXY=1 is set at startup (Node >= 22.21).
if ((process.env.HTTPS_PROXY || process.env.https_proxy) && !process.env.NODE_USE_ENV_PROXY) {
  const r = spawnSync(process.execPath, process.argv.slice(1), { stdio: "inherit", env: { ...process.env, NODE_USE_ENV_PROXY: "1" } });
  process.exit(r.status ?? 1);
}

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { values: v, positionals } = parseArgs({
  allowPositionals: true,
  options: { subsets: { type: "string", default: "latin,latin-ext" }, out: { type: "string", default: path.join(REPO, "assets/fonts") } },
});
if (!positionals.length) {
  console.log('Usage: node tools/fetch-fonts.mjs "Family:axes" ["Family2:axes" ...] [--subsets latin,latin-ext] [--out dir]');
  process.exit(2);
}
// A current Chrome user agent makes the API answer with woff2 and unicode-range subsets.
const UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36";
const subsets = new Set(v.subsets.split(","));

for (const spec of positionals) {
  const family = spec.split(":")[0];
  const slug = family.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const url = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(spec).replace(/%20/g, "+")}&display=block`;
  const res = await fetch(url, { headers: { "user-agent": UA } });
  if (!res.ok) throw new Error(`${res.status} for ${url}`);
  const css = await res.text();
  const dir = path.join(v.out, slug);
  fs.mkdirSync(dir, { recursive: true });
  // The response is a list of "/* subset */ @font-face { ... }" blocks.
  const blocks = [...css.matchAll(/\/\*\s*([\w-]+)\s*\*\/\s*(@font-face\s*{[^}]+})/g)];
  let out = `/* ${family} from Google Fonts (SIL OFL 1.1), fetched ${new Date().toISOString().slice(0, 10)}\n   ${url} */\n`;
  let n = 0;
  for (const [, subset, block] of blocks) {
    if (!subsets.has(subset)) continue;
    const src = block.match(/url\((https:[^)]+)\)/)[1];
    const r = await fetch(src);
    if (!r.ok) throw new Error(`${r.status} for ${src}`);
    const buf = Buffer.from(await r.arrayBuffer());
    const style = (block.match(/font-style:\s*(\w+)/) || [])[1] || "normal";
    // Variable families return the same file for every weight: name by content so it is stored once.
    const name = `${slug}-${subset}-${style}-${crypto.createHash("sha1").update(buf).digest("hex").slice(0, 8)}.woff2`;
    fs.writeFileSync(path.join(dir, name), buf);
    out += `/* ${subset} */\n` + block.replace(src, `${slug}/${name}`) + "\n";
    n++;
  }
  fs.writeFileSync(path.join(v.out, `${slug}.css`), out);
  console.log(`${family}: ${n} faces, ${new Set(fs.readdirSync(dir)).size} files -> ${path.relative(REPO, dir)}/, stylesheet ${path.relative(REPO, path.join(v.out, slug + ".css"))}`);
}
