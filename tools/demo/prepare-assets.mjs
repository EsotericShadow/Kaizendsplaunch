// Copy the demo image sequence into the gitignored assets/ folder.
// Source: the kaizendsp.com website repo (public marketing frames), not committed here.
//
//   node tools/demo/prepare-assets.mjs [--src /home/user/kaizendsp/public/film/hero-frames/desktop]

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const argv = process.argv.slice(2);
const srcArg = argv.indexOf("--src");
const src = srcArg >= 0 ? argv[srcArg + 1] : "/home/user/kaizendsp/public/film/hero-frames/desktop";
const dst = path.join(repo, "assets/demo/hero");

if (!fs.existsSync(src)) {
  console.error(`Source frames not found: ${src}`);
  process.exit(1);
}
fs.mkdirSync(dst, { recursive: true });
const files = fs.readdirSync(src).filter((f) => /^frame-\d{3}\.webp$/.test(f)).sort();
for (const f of files) fs.copyFileSync(path.join(src, f), path.join(dst, f));
console.log(`Copied ${files.length} frames to ${path.relative(repo, dst)}/`);
