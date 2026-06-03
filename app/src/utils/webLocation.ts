/** `window` existe no RN/Hermes, mas `window.location` muitas vezes não — evita crash em `.origin`. */

export function getWebLocation():
  | Pick<Location, "hostname" | "port" | "protocol" | "origin">
  | null {
  if (typeof window === "undefined") return null;
  const loc = (window as Window & { location?: Location }).location;
  if (!loc || typeof loc !== "object") return null;
  return loc;
}

export function getWebOrigin(): string {
  const loc = getWebLocation();
  if (!loc?.origin || loc.origin === "null") return "";
  return loc.origin;
}

/** Evita crash no Android (expo-router / axios usam `window.location.origin`). */
export function installWebLocationShim(): void {
  if (typeof window === "undefined") return;
  const w = window as Window & { location?: Location };
  if (w.location?.origin) return;
  const stub = {
    href: "https://localhost/",
    origin: "https://localhost",
    hostname: "localhost",
    protocol: "https:",
    port: "",
    pathname: "/",
    search: "",
    hash: "",
  } as Location;
  try {
    Object.defineProperty(w, "location", {
      value: stub,
      writable: true,
      configurable: true,
    });
  } catch {
    w.location = stub;
  }
}

installWebLocationShim();
