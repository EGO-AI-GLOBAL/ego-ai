import type { PersonaChoice } from "@/constants/personas";
import {
  deleteSecureItem,
  getSecureItem,
  saveSecureItem,
} from "@/storage/sessionStorage";

function configuredKey(userId: string): string {
  return `ego_persona_ok_${userId}`;
}

function choiceKey(userId: string): string {
  return `ego_persona_choice_${userId}`;
}

/** Marca assistente escolhido (evita loop se o servidor demorar a sincronizar). */
export async function markPersonaConfiguredLocal(userId: string): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  await saveSecureItem(configuredKey(uid), "1");
}

export async function isPersonaConfiguredLocal(userId: string): Promise<boolean> {
  const uid = userId.trim();
  if (!uid) return false;
  const v = await getSecureItem(configuredKey(uid));
  return v === "1";
}

/** Guarda Leo/Luna no telemóvel se o servidor ainda devolver Luna por engano. */
export async function saveLocalPersonaChoice(
  userId: string,
  choice: PersonaChoice
): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  await saveSecureItem(
    choiceKey(uid),
    JSON.stringify({
      avatar_id: choice.avatar_id,
      voice_id: choice.voice_id,
      ts: Date.now(),
    })
  );
}

export async function getLocalPersonaChoice(
  userId: string
): Promise<PersonaChoice | null> {
  const uid = userId.trim();
  if (!uid) return null;
  const raw = await getSecureItem(choiceKey(uid));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as {
      avatar_id?: string;
      voice_id?: string;
    };
    const avatar_id = String(parsed.avatar_id || "").trim();
    const voice_id = String(parsed.voice_id || "").trim();
    if (!avatar_id || !voice_id) return null;
    return { avatar_id, voice_id };
  } catch {
    return null;
  }
}

/** Apaga escolha local (Keychain sobrevive reinstall no iOS). */
export async function clearLocalPersonaForUser(userId: string): Promise<void> {
  const uid = userId.trim();
  if (!uid) return;
  await deleteSecureItem(configuredKey(uid));
  await deleteSecureItem(choiceKey(uid));
}
