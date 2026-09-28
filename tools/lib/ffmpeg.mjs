// ffmpeg helpers: locate the binary, build encoder arguments, run and probe.

import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";

let cached = null;

/**
 * Find a full ffmpeg build (needs libx264 + aac). Order: $FFMPEG, the imageio_ffmpeg binary
 * from Python, then `ffmpeg` on PATH. Playwright's own ffmpeg (VP8 only) is not usable.
 */
export function findFfmpeg() {
  if (cached) return cached;
  const candidates = [];
  if (process.env.FFMPEG) candidates.push(process.env.FFMPEG);
  const py = spawnSync("python3", ["-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"], {
    encoding: "utf8",
  });
  if (py.status === 0 && py.stdout.trim()) candidates.push(py.stdout.trim());
  candidates.push("ffmpeg");
  for (const c of candidates) {
    const r = spawnSync(c, ["-hide_banner", "-encoders"], { encoding: "utf8" });
    if (r.status === 0 && r.stdout.includes("libx264")) {
      cached = c;
      return c;
    }
  }
  throw new Error("No ffmpeg with libx264 found. Set FFMPEG=/path/to/ffmpeg or pip install imageio-ffmpeg.");
}

/**
 * Video encoder arguments for the final delivery format.
 * H.264 High, yuv420p, BT.709 matrix + tags, limited range.
 *
 * The explicit conversion matters: left alone, ffmpeg converts RGB to YUV with the BT.601
 * matrix while the file is tagged BT.709, which shifts every colour (greens and purples most).
 *
 * zscale (zimg) is used rather than swscale: it is accurate and about 6x faster than
 * swscale with accurate_rnd+full_chroma_int at 1080p (145 vs 22 fps, one thread).
 * JPEG frames arrive as full-range BT.601 YCbCr with centred chroma (JFIF); PNG frames as RGB.
 * Output chroma is left-sited, the H.264 / MPEG-2 default.
 */
export function colorFilter({ inputIsJpeg = false, dither = "none" } = {}) {
  const src = inputIsJpeg ? "rangein=full:matrixin=470bg:chromalin=center:" : "";
  return `zscale=${src}range=limited:matrix=709:chromal=left:filter=bicubic:dither=${dither},format=yuv420p`;
}

export function videoEncodeArgs({ fps, crf = 16, preset = "slow", threads = 4, inputIsJpeg = false, gop = null, dither = "none" }) {
  const vf = colorFilter({ inputIsJpeg, dither });
  return [
    "-vf", vf,
    "-c:v", "libx264",
    "-profile:v", "high",
    "-preset", preset,
    "-crf", String(crf),
    "-pix_fmt", "yuv420p",
    "-g", String(gop || Math.round(fps * 2)),
    "-threads", String(threads),
    "-colorspace", "bt709",
    "-color_primaries", "bt709",
    "-color_trc", "bt709",
    "-color_range", "tv",
  ];
}

/** Run ffmpeg to completion. Resolves { code, stderr }. Rejects on non-zero exit. */
export function runFfmpeg(args, { ffmpeg = findFfmpeg(), timeoutMs = 0 } = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(ffmpeg, ["-hide_banner", "-nostdin", "-y", ...args], { stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    p.stderr.on("data", (d) => {
      stderr += d;
      if (stderr.length > 200_000) stderr = stderr.slice(-100_000);
    });
    let timer = null;
    if (timeoutMs) timer = setTimeout(() => p.kill("SIGKILL"), timeoutMs);
    p.on("error", reject);
    p.on("close", (code) => {
      if (timer) clearTimeout(timer);
      if (code === 0) resolve({ code, stderr });
      else reject(new Error(`ffmpeg exited ${code}:\n${stderr.slice(-3000)}`));
    });
  });
}

/**
 * Count video frames and read the stream description without ffprobe (the imageio build has
 * none). Nothing is decoded: packets are stream-copied into the framecrc muxer, one line each.
 * (The "frame=" progress counter is not printed for stream copy in ffmpeg 7, so do not parse it.)
 */
export function probeVideo(file, { ffmpeg = findFfmpeg() } = {}) {
  if (!fs.existsSync(file)) return Promise.reject(new Error(`probeVideo: missing ${file}`));
  return new Promise((resolve, reject) => {
    const p = spawn(ffmpeg, ["-hide_banner", "-nostdin", "-i", file, "-map", "0:v:0", "-c", "copy", "-f", "framecrc", "-"], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stderr = "";
    let frames = 0;
    let rest = "";
    p.stdout.on("data", (d) => {
      const lines = (rest + d).split("\n");
      rest = lines.pop();
      for (const l of lines) if (l && !l.startsWith("#")) frames++;
    });
    p.stderr.on("data", (d) => (stderr += d));
    p.on("error", reject);
    p.on("close", (code) => {
      if (rest && !rest.startsWith("#")) frames++;
      if (code !== 0) return reject(new Error(`probeVideo(${file}) failed: ${stderr.slice(-1500)}`));
      const stream = (stderr.match(/Stream #0:\d+[^:]*: Video: ([^\n]+)/) || [])[1] || "";
      const audio = (stderr.match(/Stream #0:\d+[^:]*: Audio: ([^\n]+)/) || [])[1] || "";
      const dur = (stderr.match(/Duration: (\d+):(\d+):([\d.]+)/) || []).slice(1).map(Number);
      resolve({
        frames,
        video: stream.trim(),
        audio: audio.trim(),
        duration: dur.length ? dur[0] * 3600 + dur[1] * 60 + dur[2] : NaN,
      });
    });
  });
}
