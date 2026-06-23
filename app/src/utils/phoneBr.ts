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

/** +5511999887766 → (11) 99988-7766 */
export function formatPhoneBrDisplay(e164: string): string {
  const digits = e164.replace(/\D/g, "");
  const local = digits.startsWith("55") ? digits.slice(2) : digits;
  if (local.length === 11) {
    return `(${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7)}`;
  }
  if (local.length === 10) {
    return `(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`;
  }
  return e164;
}
