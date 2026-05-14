/**
 * Prefer same-origin API in production (behind Nginx):
 * - Browser requests `/api/...` (no :8000)
 * - Nginx proxies `/api` -> `127.0.0.1:8000/api`
 *
 * For local dev you can either:
 * - rely on Next `rewrites()` (recommended; see next.config.mjs), or
 * - set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
export const OCR_PROVIDER = process.env.NEXT_PUBLIC_OCR_PROVIDER;

export type HealthResponse = { status: string };

export type TicketPlayType = "SPF" | "RQSPF";

export type TicketLeg = {
  matchKey: string;
  playType?: TicketPlayType | null;
  selection: string;
  handicap: number | null;
  sp: number;
};

export type Ticket = {
  ticketType: string;
  playType: TicketPlayType;
  multiplier: number;
  passTypes: string[];
  legs: TicketLeg[];
};

export type TicketDraft = {
  ticket: Ticket;
  warnings?: string[];
  confidence?: Record<string, unknown>;
  sourceImages?: string[];
};

export type RecognizeTicketResponse = { id: string; anonToken?: string } & TicketDraft;

export type ValidateTicketResponse = { ok: true } | { ok: false; errors: string[] };

export type CalculateTicketResponse =
  | { ok: false; errors: string[] }
  | { id: string; report: Record<string, unknown> };

export type GetTicketResponse = {
  id: string;
  anonToken?: string | null;
  ticket: Ticket;
  report?: Record<string, unknown> | null;
  createdAt?: string;
};

async function apiFetch<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.json !== undefined) headers.set("Content-Type", "application/json");

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    body: init?.json !== undefined ? JSON.stringify(init.json) : init?.body,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${path}${text ? `: ${text}` : ""}`);
  }
  return (await res.json()) as T;
}

export async function recognizeTicket(files: File[]): Promise<RecognizeTicketResponse> {
  const form = new FormData();
  for (const file of files) form.append("images", file);
  const headers: HeadersInit = {};
  if (OCR_PROVIDER) headers["X-Ocr-Provider"] = OCR_PROVIDER;
  return await apiFetch<RecognizeTicketResponse>("/api/tickets/recognize", {
    method: "POST",
    headers,
    body: form,
  });
}

export async function getTicket(id: string): Promise<GetTicketResponse> {
  return await apiFetch<GetTicketResponse>(`/api/tickets/${encodeURIComponent(id)}`);
}

export async function validateTicket(ticket: Ticket): Promise<ValidateTicketResponse> {
  return await apiFetch<ValidateTicketResponse>("/api/tickets/validate", {
    method: "POST",
    json: ticket,
  });
}

export async function calculateTicket(ticket: Ticket): Promise<CalculateTicketResponse> {
  return await apiFetch<CalculateTicketResponse>("/api/tickets/calculate", {
    method: "POST",
    json: ticket,
  });
}
