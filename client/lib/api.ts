const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export const UNAUTHORIZED_EVENT = "jk:unauthorized";

export type ApiErrorDetails = Record<string, unknown>;

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ApiErrorDetails | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: ApiErrorDetails | null,
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type ErrorBody = {
  error?: { code?: string; message?: string; details?: ApiErrorDetails };
};

export type ApiInit = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  json?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
};

export async function apiFetch<T>(path: string, init: ApiInit = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", ...init.headers };
  if (init.json !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: init.method ?? "GET",
      headers,
      body: init.json !== undefined ? JSON.stringify(init.json) : undefined,
      signal: init.signal,
      credentials: "same-origin",
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiRequestError(0, "network_error", "Tidak dapat terhubung ke server", null);
  }

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && path !== "/v1/auth/login" && typeof window !== "undefined") {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    const error = (body as ErrorBody | null)?.error;
    throw new ApiRequestError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? `Permintaan gagal (${response.status})`,
      error?.details ?? null,
    );
  }
  return body as T;
}

export function toQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function describeError(error: unknown): string {
  if (error instanceof ApiRequestError) {
    const fields = error.details?.fields;
    if (Array.isArray(fields) && fields.length > 0) {
      const first = fields[0] as { field?: string; message?: string };
      return `${error.message}${first?.field ? ` (${first.field}: ${first.message})` : ""}`;
    }
    return error.message;
  }
  return "Terjadi kesalahan yang tidak terduga";
}
