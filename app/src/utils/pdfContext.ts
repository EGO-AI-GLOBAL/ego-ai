import * as FileSystem from "expo-file-system";
import { Platform } from "react-native";
import { API_V1 } from "@/constants/config";
import { api, ApiClientError, getSession } from "@/api/client";

/** Alinhado ao limite do botão «Carregar PDFs» no Streamlit. */
export const PDF_STORE_MAX_CHARS = 200_000;

/** Formatos aceites (servidor `ego_api/document_extract.py`). */
export const SUPPORTED_DOC_EXTENSIONS = [
  ".pdf",
  ".txt",
  ".md",
  ".markdown",
  ".csv",
  ".tsv",
  ".json",
  ".xml",
  ".html",
  ".htm",
  ".log",
  ".rst",
  ".docx",
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".heic",
  ".heif",
] as const;

export const SUPPORTED_DOC_LABEL =
  "PDF, Word, TXT, fotos (JPG/PNG), galeria ou câmara";

/** Tipos para o DocumentPicker (Expo). */
export const DOCUMENT_PICKER_MIME_TYPES = [
  "application/pdf",
  "text/plain",
  "text/markdown",
  "text/csv",
  "text/html",
  "text/xml",
  "application/json",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
  "*/*",
] as const;

const MIME_BY_EXT: Record<string, string> = {
  ".pdf": "application/pdf",
  ".txt": "text/plain",
  ".md": "text/plain",
  ".markdown": "text/plain",
  ".csv": "text/csv",
  ".tsv": "text/csv",
  ".json": "application/json",
  ".xml": "text/xml",
  ".html": "text/html",
  ".htm": "text/html",
  ".log": "text/plain",
  ".rst": "text/plain",
  ".docx":
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".heic": "image/heic",
  ".heif": "image/heif",
};

export function isSupportedDocName(name: string): boolean {
  const lower = (name || "").trim().toLowerCase();
  return SUPPORTED_DOC_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function mimeForFilename(name: string): string {
  const lower = name.toLowerCase();
  for (const ext of SUPPORTED_DOC_EXTENSIONS) {
    if (lower.endsWith(ext)) return MIME_BY_EXT[ext] ?? "application/octet-stream";
  }
  return "application/octet-stream";
}

export type PdfExtractResult = {
  text: string;
  char_count: number;
  warnings: string[];
};

export function uiStateFromProfile(
  profile: Record<string, unknown> | null | undefined
): Record<string, unknown> {
  if (!profile) return {};
  const raw = profile.ui_state;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    return raw as Record<string, unknown>;
  }
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw) as unknown;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return {};
    }
  }
  return {};
}

export function pdfContextFromProfile(
  profile: Record<string, unknown> | null | undefined
): string {
  const ui = uiStateFromProfile(profile);
  const pdf = ui.pdf_context;
  return typeof pdf === "string" ? pdf : "";
}

/** Número de PDFs/páginas anexados em sequência (uma escolha por vez). */
export function pdfAttachmentCountFromProfile(
  profile: Record<string, unknown> | null | undefined
): number {
  const ui = uiStateFromProfile(profile);
  const n = ui.pdf_attachment_count;
  if (typeof n === "number" && n > 0) return Math.floor(n);
  const text = pdfContextFromProfile(profile);
  return text.trim() ? 1 : 0;
}

export const PDF_PART_SEPARATOR = "\n\n---\n\n";

export function mergePdfContextParts(...parts: string[]): string {
  return parts.map((p) => (p || "").trim()).filter(Boolean).join(PDF_PART_SEPARATOR);
}

export function capPdfForStore(text: string): string {
  const t = (text || "").trim();
  if (t.length <= PDF_STORE_MAX_CHARS) return t;
  return t.slice(0, PDF_STORE_MAX_CHARS);
}

function parsePdfExtractResponse(data: unknown): PdfExtractResult {
  const body = data as {
    ok?: boolean;
    error?: string;
    text?: string;
    char_count?: number;
    warnings?: string[];
  };
  if (body?.ok === false) {
    throw new Error(body.error || "Falha ao ler o documento.");
  }
  const text = String(body.text || "").trim();
  if (!text) {
    throw new Error(body.error || "O ficheiro não tem texto legível.");
  }
  return {
    text,
    char_count: body.char_count ?? text.length,
    warnings: Array.isArray(body.warnings) ? body.warnings : [],
  };
}

function mapPdfUploadError(err: unknown): Error {
  if (err instanceof ApiClientError && err.status === 404) {
    return new Error(
      "Leitura de documentos indisponível no servidor (API desatualizada). " +
        "Aguarde o deploy no Railway e tente de novo."
    );
  }
  const msg = err instanceof Error ? err.message : "Não foi possível enviar o documento.";
  if (/Network Error|ERR_NETWORK|timeout|timed out/i.test(msg)) {
    return new Error(
      "Falha ao enviar o documento. Use Wi‑Fi estável, PDF até 12 MB, ou tente um ficheiro .txt pequeno para testar."
    );
  }
  return new Error(msg);
}

/** Android/iOS: upload nativo (axios FormData falha com frequência em produção). */
async function extractPdfUploadNative(
  uri: string,
  name: string
): Promise<PdfExtractResult> {
  const session = getSession();
  const token = session?.access_token?.trim();
  if (!token) {
    throw new Error("Sessão expirada. Saia e entre novamente.");
  }
  const base = API_V1.endsWith("/") ? API_V1 : `${API_V1}/`;
  const url = `${base}pdf/extract`;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (session?.refresh_token) {
    headers["X-Refresh-Token"] = session.refresh_token;
  }
  const res = await FileSystem.uploadAsync(url, uri, {
    httpMethod: "POST",
    uploadType: FileSystem.FileSystemUploadType.MULTIPART,
    fieldName: "pdf",
    mimeType: mimeForFilename(name),
    headers,
  });
  if (res.status < 200 || res.status >= 300) {
    let detail = `Erro ${res.status} ao enviar o documento.`;
    try {
      const parsed = JSON.parse(res.body) as { error?: string };
      if (parsed.error) detail = parsed.error;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  try {
    return parsePdfExtractResponse(JSON.parse(res.body));
  } catch {
    throw new Error("Resposta inválida do servidor ao ler o documento.");
  }
}

export async function extractPdfUploads(
  files: Array<{ uri: string; name: string }>
): Promise<PdfExtractResult> {
  if (!files.length) {
    throw new Error("Nenhum ficheiro selecionado.");
  }
  for (const f of files) {
    const name = (f.name || "documento.txt").trim();
    if (!isSupportedDocName(name)) {
      throw new Error(`Formato não suportado. Use: ${SUPPORTED_DOC_LABEL}.`);
    }
  }

  if (Platform.OS !== "web") {
    const warnings: string[] = [];
    const texts: string[] = [];
    try {
      for (const f of files) {
        const part = await extractPdfUploadNative(f.uri, f.name);
        texts.push(part.text);
        warnings.push(...part.warnings);
      }
      const text = mergePdfContextParts(...texts);
      return {
        text,
        char_count: text.length,
        warnings,
      };
    } catch (err: unknown) {
      throw mapPdfUploadError(err);
    }
  }

  const form = new FormData();
  for (const f of files) {
    const name = (f.name || "documento.txt").trim();
    const res = await fetch(f.uri);
    const blob = await res.blob();
    form.append("pdf", blob, name);
  }
  try {
    const res = await api.post("pdf/extract", form, {
      timeout: 120_000,
      maxBodyLength: Infinity,
      maxContentLength: Infinity,
    });
    return parsePdfExtractResponse(res.data);
  } catch (err: unknown) {
    throw mapPdfUploadError(err);
  }
}

export async function persistPdfContext(
  pdfText: string,
  profile: Record<string, unknown> | null | undefined,
  opts?: { attachmentCount?: number }
): Promise<{ charCount: number; truncated: boolean; text: string }> {
  const ui = uiStateFromProfile(profile);
  const capped = capPdfForStore(pdfText);
  const truncated = capped.length < (pdfText || "").trim().length;
  const count =
    typeof opts?.attachmentCount === "number" && opts.attachmentCount > 0
      ? Math.floor(opts.attachmentCount)
      : capped.trim()
        ? 1
        : 0;
  await api.patch("profile", {
    ui_state: {
      ...ui,
      v: typeof ui.v === "number" ? ui.v : 1,
      pdf_context: capped,
      pdf_truncated: truncated,
      pdf_attachment_count: count,
    },
  });
  return { charCount: capped.length, truncated, text: capped };
}

export async function clearPdfContext(
  profile: Record<string, unknown> | null | undefined
): Promise<void> {
  const ui = uiStateFromProfile(profile);
  await api.patch("profile", {
    ui_state: {
      ...ui,
      pdf_context: "",
      pdf_truncated: false,
      pdf_attachment_count: 0,
    },
  });
}
