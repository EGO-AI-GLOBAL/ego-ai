import { deleteSecureItem, getSecureItem, saveSecureItem } from "@/storage/sessionStorage";

const KEY = "ego_post_login_route_v1";

export type PostLoginRoute = "/(main)/agenda" | "/(main)/chat";

export async function savePostLoginRoute(route: PostLoginRoute): Promise<void> {
  await saveSecureItem(KEY, route);
}

export async function consumePostLoginRoute(): Promise<PostLoginRoute | null> {
  const raw = await getSecureItem(KEY);
  await deleteSecureItem(KEY);
  const v = (raw || "").trim();
  if (v === "/(main)/agenda" || v === "/(main)/chat") return v;
  return null;
}
