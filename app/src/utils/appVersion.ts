/** Compara versões semver simples (ex.: 1.0.9 vs 1.0.11). */
export function parseAppVersion(raw: string): number[] {
  const clean = (raw || "")
    .trim()
    .replace(/^ego-ai@/i, "")
    .split(/[+\s]/)[0];
  return clean.split(".").map((part) => {
    const n = parseInt(part.replace(/\D/g, ""), 10);
    return Number.isFinite(n) ? n : 0;
  });
}

export function isAppVersionBehind(current: string, latest: string): boolean {
  const a = parseAppVersion(current);
  const b = parseAppVersion(latest);
  const len = Math.max(a.length, b.length);
  for (let i = 0; i < len; i += 1) {
    const left = a[i] ?? 0;
    const right = b[i] ?? 0;
    if (left < right) return true;
    if (left > right) return false;
  }
  return false;
}
