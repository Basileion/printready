const ORIGIN = "https://cdn.jsdelivr.net/gh/Basileion/printready@main/site";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    let path = url.pathname;
    if (path === "/" || path === "") path = "/index.html";
    else if (path.endsWith("/")) path = path + "index.html";

    const upstream = ORIGIN + path;
    const res = await fetch(upstream, {
      cf: { cacheTtl: 60, cacheEverything: true },
      headers: { "User-Agent": "PrintReadyWorker/1.0" },
    });
    if (res.status === 404 && !path.endsWith(".html")) {
      const retry = await fetch(ORIGIN + path.replace(/\/?$/, "/index.html"));
      if (retry.ok) {
        return new Response(retry.body, {
          status: 200,
          headers: withHeaders(retry, path + "/index.html"),
        });
      }
    }
    if (!res.ok) {
      return new Response("Not found", { status: res.status });
    }
    return new Response(res.body, {
      status: res.status,
      headers: withHeaders(res, path),
    });
  },
};

function withHeaders(res, path) {
  const h = new Headers(res.headers);
  h.set("X-Content-Type-Options", "nosniff");
  h.set("Cache-Control", "public, max-age=60");
  if (path.endsWith(".html")) h.set("Content-Type", "text/html; charset=utf-8");
  else if (path.endsWith(".css")) h.set("Content-Type", "text/css; charset=utf-8");
  else if (path.endsWith(".js")) h.set("Content-Type", "application/javascript; charset=utf-8");
  else if (path.endsWith(".xml")) h.set("Content-Type", "application/xml; charset=utf-8");
  else if (path.endsWith(".txt")) h.set("Content-Type", "text/plain; charset=utf-8");
  else if (path.endsWith(".png")) h.set("Content-Type", "image/png");
  else if (path.endsWith(".svg")) h.set("Content-Type", "image/svg+xml");
  h.delete("content-encoding");
  return h;
}
