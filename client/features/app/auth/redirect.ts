export function loginUrl(from: string): string {
  return from && from !== "/" ? `/masuk?lanjut=${encodeURIComponent(from)}` : "/masuk";
}

export function safeNext(value: string | null): string | null {
  if (!value) return null;
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return null;
  return value;
}
