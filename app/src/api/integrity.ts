import { api } from "@/api/client";

export type IntegrityStatus = {
  enabled: boolean;
  mode: string;
  server_configured: boolean;
  package_name: string;
  project_number: string | null;
};

export async function fetchIntegrityStatus(): Promise<IntegrityStatus | null> {
  try {
    const { data } = await api.get<{ ok?: boolean } & IntegrityStatus>("integrity/status");
    if (data && data.ok !== false) {
      return {
        enabled: Boolean(data.enabled),
        mode: String(data.mode || "monitor"),
        server_configured: Boolean(data.server_configured),
        package_name: String(data.package_name || ""),
        project_number: data.project_number ?? null,
      };
    }
  } catch {
    /* ignore */
  }
  return null;
}
