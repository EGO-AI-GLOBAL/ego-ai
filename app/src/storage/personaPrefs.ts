import { getSecureItem, saveSecureItem } from "@/storage/sessionStorage";

function key(userId: string): string {
  return `ego_persona_ok_${userId}`;
}

/** Marca assistente escolhido (evita loop se o servidor demorar a sincronizar). */
export async function markPersonaConfiguredLocal(userId: string): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  await saveSecureItem(key(uid), "1");
}

export async function isPersonaConfiguredLocal(userId: string): Promise<boolean> {
  const uid = userId.trim();
  if (!uid) return false;
  const v = await getSecureItem(key(uid));
  return v === "1";
}
