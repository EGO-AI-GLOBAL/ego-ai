import { Platform } from "react-native";
import { api, ApiClientError } from "@/api/client";

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

export async function extractPdfUploads(
  files: Array<{ uri: string; name: string }>
): Promise<PdfExtractResult> {
  if (!files.length) {
    throw new Error("Nenhum ficheiro selecionado.");
  }
  const form = new FormData();
  for (const f of files) {
    const name = (f.name || "documento.txt").trim();
    if (!isSupportedDocName(name)) {
      throw new Error(`Formato não suportado. Use: ${SUPPORTED_DOC_LABEL}.`);
    }
    const mime = mimeForFilename(name);
    if (Platform.OS === "web") {
      const res = await fetch(f.uri);
      const blob = await res.blob();
      form.append("pdf", blob, name);
    } else {
      form.append(
        "pdf",
        { uri: f.uri, name, type: mime } as unknown as Blob
      );
    }
  }
  let data: unknown;
  try {
    const res = await api.post("pdf/extract", form, {
      timeout: 120_000,
      maxBodyLength: Infinity,
      maxContentLength: Infinity,
    });
    data = res.data;
  } catch (err: unknown) {
    if (err instanceof ApiClientError && err.status === 404) {
      throw new Error(
        "Leitura de documentos indisponível no servidor (API desatualizada). " +
          "Faça deploy do código novo no Railway."
      );
    }
    const msg =
      err instanceof Error ? err.message : "Não foi possível enviar o documento.";
    throw new Error(msg);
  }
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
