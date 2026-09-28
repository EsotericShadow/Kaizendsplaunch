// Tiny static file server for compositions. Binds to 127.0.0.1 on a free port.
//
// Serving over http:// instead of file:// avoids CORS failures for fonts, fetch() and canvas
// reads of images. Mounts map URL prefixes to directories; the longest matching prefix wins.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".htm": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".avif": "image/avif",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
  ".wav": "audio/wav",
  ".mp3": "audio/mpeg",
  ".m4a": "audio/mp4",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".bin": "application/octet-stream",
};

/**
 * startServer({ mounts: [{ prefix: "/", dir: "/abs/dir" }, ...] })
 * Returns { url, port, close(), missing: string[] } where missing collects 404 paths.
 */
export async function startServer({ mounts, log = () => {} }) {
  const table = mounts
    .map((m) => ({ prefix: m.prefix.endsWith("/") ? m.prefix : m.prefix + "/", dir: path.resolve(m.dir) }))
    .sort((a, b) => b.prefix.length - a.prefix.length);
  const missing = [];

  const server = http.createServer((req, res) => {
    let urlPath;
    try {
      urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
    } catch {
      res.writeHead(400).end("bad url");
      return;
    }
    if (req.method !== "GET" && req.method !== "HEAD") {
      res.writeHead(405).end();
      return;
    }
    const mount = table.find((m) => urlPath === m.prefix.slice(0, -1) || urlPath.startsWith(m.prefix));
    if (!mount) return notFound(res, urlPath);
    const rel = urlPath.slice(mount.prefix.length);
    let file = path.resolve(mount.dir, rel);
    if (file !== mount.dir && !file.startsWith(mount.dir + path.sep)) return notFound(res, urlPath);
    fs.stat(file, (err, st) => {
      if (!err && st.isDirectory()) {
        file = path.join(file, "index.html");
        return fs.stat(file, (err2, st2) => (err2 ? notFound(res, urlPath) : send(res, req, file, st2)));
      }
      if (err) return notFound(res, urlPath);
      send(res, req, file, st);
    });
  });

  function notFound(res, urlPath) {
    if (!urlPath.endsWith("/favicon.ico")) {
      missing.push(urlPath);
      log(`404 ${urlPath}`);
    }
    res.writeHead(404, { "content-type": "text/plain" }).end("not found");
  }

  function send(res, req, file, st) {
    const type = MIME[path.extname(file).toLowerCase()] || "application/octet-stream";
    res.writeHead(200, {
      "content-type": type,
      "content-length": st.size,
      "cache-control": "no-cache",
      "access-control-allow-origin": "*",
    });
    if (req.method === "HEAD") return res.end();
    fs.createReadStream(file).on("error", () => res.destroy()).pipe(res);
  }

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  server.keepAliveTimeout = 60_000;
  const { port } = server.address();
  return {
    port,
    url: `http://127.0.0.1:${port}`,
    missing,
    close: () =>
      new Promise((resolve) => {
        server.closeAllConnections?.();
        server.close(() => resolve());
      }),
  };
}
