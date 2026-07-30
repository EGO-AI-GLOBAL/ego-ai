/** Checkout academia → site g.html?c=CODE → API /checkout/gym/ (Connect 30%). */

const SITE =
  (typeof process !== "undefined" && process.env?.EXPO_PUBLIC_WEBSITE_URL?.trim()) ||
  "https://egoai.com.br";

export function gymCheckoutPageUrl(gymCode: string): string {
  const code = encodeURIComponent((gymCode || "").trim().toUpperCase());
  return `${SITE.replace(/\/$/, "")}/g.html?c=${code}`;
}
