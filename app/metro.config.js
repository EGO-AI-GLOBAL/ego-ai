const { getDefaultConfig } = require("expo/metro-config");
const http = require("http");
const https = require("https");

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

const envApi = (process.env.EXPO_PUBLIC_API_URL || "").replace(/\/$/, "").trim();
const FLASK_TARGET =
  process.env.EXPO_FLASK_PROXY || envApi || "http://127.0.0.1:5000";

function proxyToFlask(req, res) {
  const url = req.url || "";
  const target = new URL(url, FLASK_TARGET);
  const transport = target.protocol === "https:" ? https : http;
  const chunks = [];

  req.on("data", (chunk) => chunks.push(chunk));
  req.on("end", () => {
    const body = Buffer.concat(chunks);
    const hopByHop = new Set([
      "connection",
      "transfer-encoding",
      "keep-alive",
      "proxy-authenticate",
      "proxy-authorization",
      "te",
      "trailers",
      "upgrade",
      "host",
      "content-length",
    ]);
    const headers = {};
    for (const [key, value] of Object.entries(req.headers)) {
      if (!value || hopByHop.has(String(key).toLowerCase())) continue;
      headers[key] = value;
    }
    headers.host = target.host;
    if (body.length > 0) {
      headers["content-length"] = String(body.length);
    }

    const proxyReq = transport.request(
      target,
      { method: req.method, headers, timeout: 120_000 },
      (proxyRes) => {
        const outHeaders = { ...proxyRes.headers };
        delete outHeaders["transfer-encoding"];
        res.writeHead(proxyRes.statusCode || 502, outHeaders);
        proxyRes.pipe(res);
      }
    );
    proxyReq.setTimeout(120_000, () => {
      proxyReq.destroy(new Error("timeout"));
    });

    proxyReq.on("error", (err) => {
      res.statusCode = 502;
      res.setHeader("Content-Type", "application/json");
      res.end(
        JSON.stringify({
          ok: false,
          error: `API inacessível em ${FLASK_TARGET}. Verifique Railway ou python flask_api.py`,
          detail: String(err.message || err),
        })
      );
    });

    if (body.length > 0) {
      proxyReq.end(body);
    } else {
      proxyReq.end();
    }
  });

  req.on("error", () => {
    res.statusCode = 400;
    res.end();
  });
}

config.server = {
  ...config.server,
  enhanceMiddleware: (middleware) => {
    return (req, res, next) => {
      const url = req.url || "";
      if (url.startsWith("/api")) {
        proxyToFlask(req, res);
        return;
      }
      return middleware(req, res, next);
    };
  },
};

module.exports = config;
