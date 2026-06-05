import type { SharedCalendarMember } from "@/api/types";

function invitedEmail(m: SharedCalendarMember): string {
  return (m.invited_email || "").trim().toLowerCase();
}

function isEmailLike(text: string): boolean {
  const t = text.trim().toLowerCase();
  return t.includes("@") || t.endsWith(".com") || t.endsWith(".br");
}

/** Formata parte local do e-mail como nome legível (nunca mostra @). */
export function prettyNameFromEmail(emailOrLocal: string): string {
  const raw = (emailOrLocal || "").trim().toLowerCase();
  if (!raw) return "Membro";
  const local = raw.includes("@") ? raw.split("@")[0] : raw;
  const parts = local.replace(/[._+\-]+/g, " ").split(/\s+/).filter(Boolean);
  if (!parts.length) return "Convidado";
  return parts
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase())
    .join(" ");
}

export function memberIsPendingInvite(m: SharedCalendarMember): boolean {
  const status = (m.status || "active").toLowerCase();
  return status === "pending" || !String(m.user_id || "").trim();
}

function formatPhoneBr(e164: string): string {
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

/** Nome da pessoa — prioriza «como quer ser chamado» (full_name); nunca e-mail cru. */
export function memberDisplayName(m: SharedCalendarMember): string {
  const email = invitedEmail(m);
  const phone = (m.invited_phone || "").trim();
  const fromApi = (m.display_name || "").trim();

  if (fromApi && !isEmailLike(fromApi)) {
    const local = email.includes("@") ? email.split("@")[0] : "";
    if (!email || (fromApi.toLowerCase() !== email && fromApi.toLowerCase() !== local)) {
      return fromApi;
    }
  }

  if (phone) return formatPhoneBr(phone);
  if (email.includes("@") && email.includes("@invite.ego")) {
    const digits = email.split("@")[0].replace(/^phone/, "");
    if (digits) return formatPhoneBr("+" + digits);
  }
  if (email.includes("@")) return prettyNameFromEmail(email);
  if (fromApi) return prettyNameFromEmail(fromApi);
  return "Membro";
}

function memberStatusHint(m: SharedCalendarMember): string | null {
  if (!memberIsPendingInvite(m)) return null;
  return "convidado";
}

export function membersSummary(
  members: SharedCalendarMember[] | undefined,
  maxNames = 3
): string {
  if (!members?.length) return "";
  const names = members.map(memberDisplayName);
  if (names.length <= maxNames) return names.join(", ");
  const head = names.slice(0, maxNames).join(", ");
  return `${head} +${names.length - maxNames}`;
}

export function membersCardLine(
  members: SharedCalendarMember[] | undefined,
  memberCount?: number,
  myUserId?: string
): string {
  if (members?.length) {
    return members
      .map((m) => {
        const name = memberDisplayName(m);
        const bits: string[] = [];
        if (myUserId && String(m.user_id || "") === myUserId) bits.push("você");
        else if (m.role === "owner") bits.push("criador");
        const pending = memberStatusHint(m);
        if (pending) bits.push(pending);
        return bits.length ? `${name} (${bits.join(", ")})` : name;
      })
      .join("\n");
  }
  const n = memberCount ?? 0;
  if (n > 0) {
    return `${n} pessoa${n === 1 ? "" : "s"} no grupo — puxe a lista para baixo para carregar`;
  }
  return "";
}

export function membersGroupLine(
  members: SharedCalendarMember[] | undefined,
  myUserId?: string
): string {
  if (!members?.length) return "Nenhuma pessoa adicionada ainda.";
  return members
    .map((m) => {
      const name = memberDisplayName(m);
      const bits: string[] = [];
      if (m.role === "owner") bits.push("criador");
      if (myUserId && String(m.user_id || "") === myUserId) bits.push("você");
      const pending = memberStatusHint(m);
      if (pending) bits.push(pending);
      return bits.length ? `${name} (${bits.join(", ")})` : name;
    })
    .join("\n");
}
