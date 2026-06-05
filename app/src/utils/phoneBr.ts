/** Formata telefone BR enquanto o utilizador digita (DDD + número). */
export function formatPhoneBrInput(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, 13);
  if (!digits.length) return "";

  let local = digits;
  if (digits.startsWith("55") && digits.length > 11) {
    local = digits.slice(2);
  }

  if (local.length <= 2) {
    return local.length === 2 ? `(${local}) ` : local;
  }
  if (local.length <= 6) {
    return `(${local.slice(0, 2)}) ${local.slice(2)}`;
  }
  if (local.length <= 10) {
    return `(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`;
  }
  return `(${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7, 11)}`;
}
