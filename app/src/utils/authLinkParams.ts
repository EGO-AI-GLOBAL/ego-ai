/** Extrai access_token / refresh_token do hash ou query de links Supabase. */
export function authTokensFromUrl(url: string): {
  access_token?: string;
  refresh_token?: string;
  type?: string;
} {
  const out: { access_token?: string; refresh_token?: string; type?: string } = {};
  const ingest = (chunk: string) => {
    if (!chunk) return;
    for (const part of chunk.split("&")) {
      const eq = part.indexOf("=");
      if (eq < 1) continue;
      const key = decodeURIComponent(part.slice(0, eq));
      const val = decodeURIComponent(part.slice(eq + 1));
      if (key === "access_token") out.access_token = val;
      if (key === "refresh_token") out.refresh_token = val;
      if (key === "type") out.type = val;
    }
  };
  const hashIdx = url.indexOf("#");
  if (hashIdx >= 0) ingest(url.slice(hashIdx + 1));
  const qIdx = url.indexOf("?");
  if (qIdx >= 0) {
    const end = hashIdx >= 0 ? hashIdx : url.length;
    ingest(url.slice(qIdx + 1, end));
  }
  return out;
}
