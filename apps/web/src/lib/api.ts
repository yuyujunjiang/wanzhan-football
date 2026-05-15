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

export type LedgerStatus = "pending" | "settled";
export type LedgerMode = "schedule" | "results";

export type LedgerLegInput = {
  matchKey: string;
  matchId?: number | null;
  league: string;
  homeTeam: string;
  awayTeam: string;
  kickoffTime?: string | null;
  playType: TicketPlayType;
  selection: string;
  sp: number;
  handicap?: number | null;
};

export type LedgerLeg = LedgerLegInput & {
  id: number;
  resultSelection?: string | null;
  isHit?: boolean | null;
};

export type LedgerTicket = {
  id: string;
  date: string;
  status: LedgerStatus;
  passType: string;
  multiplier: number;
  stake: number;
  estimatedPayout: number;
  actualPayout: number;
  profit: number;
  createdAt: number;
  settledAt?: number | null;
  legs: LedgerLeg[];
};

export type LedgerSummary = {
  stake: number;
  payout: number;
  profit: number;
  pendingCount: number;
  settledCount: number;
  ticketCount: number;
};

export type AuthUser = { id: string; username: string };

type ApiFetchInit = RequestInit & {
  json?: unknown;
  /** When true, a 401 does not redirect to login (used by the login page). */
  skipAuthRedirect?: boolean;
};

function redirectToLoginIfNeeded(path: string, status: number, skipAuthRedirect?: boolean) {
  if (typeof window === "undefined") return;
  if (status !== 401) return;
  if (skipAuthRedirect) return;
  if (path.startsWith("/api/auth/login")) return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `/wanzhan/login?next=${next}`;
}

async function apiFetch<T>(
  path: string,
  init?: ApiFetchInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.json !== undefined) headers.set("Content-Type", "application/json");

  const { json, skipAuthRedirect, ...rest } = init ?? {};
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    credentials: "include",
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  redirectToLoginIfNeeded(path, res.status, skipAuthRedirect);

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${path}${text ? `: ${text}` : ""}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  const raw = await res.text();
  if (!raw) {
    return undefined as T;
  }
  return JSON.parse(raw) as T;
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
    skipAuthRedirect: true,
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

export async function createLedgerTicket(input: {
  mode: LedgerMode;
  date: string;
  multiplier: number;
  legs: LedgerLegInput[];
}): Promise<LedgerTicket> {
  return await apiFetch<LedgerTicket>("/api/ledger/tickets", {
    method: "POST",
    json: input,
  });
}

export async function settleLedgerTickets(): Promise<{ settledCount: number }> {
  return await apiFetch<{ settledCount: number }>("/api/ledger/settle", {
    method: "POST",
  });
}

export async function getLedgerSummary(start: string, end: string): Promise<LedgerSummary> {
  return await apiFetch<LedgerSummary>(
    `/api/ledger/summary?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
  );
}

export async function listLedgerTickets(input: {
  date?: string;
  start?: string;
  end?: string;
  status?: "all" | "pending" | "settled";
}): Promise<LedgerTicket[]> {
  const params = new URLSearchParams();
  if (input.date) params.set("date", input.date);
  if (input.start) params.set("start", input.start);
  if (input.end) params.set("end", input.end);
  params.set("status", input.status ?? "all");
  return await apiFetch<LedgerTicket[]>(`/api/ledger/tickets?${params.toString()}`);
}

export async function getLedgerTicket(id: string): Promise<LedgerTicket> {
  return await apiFetch<LedgerTicket>(`/api/ledger/tickets/${encodeURIComponent(id)}`);
}

export async function login(username: string, password: string): Promise<AuthUser> {
  return await apiFetch<AuthUser>("/api/auth/login", {
    method: "POST",
    json: { username, password },
    skipAuthRedirect: true,
  });
}

export async function logout(): Promise<void> {
  await apiFetch<void>("/api/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<AuthUser> {
  return await apiFetch<AuthUser>("/api/auth/me");
}

export async function updateLedgerTicket(
  id: string,
  body:
    | { date: string; multiplier: number; legs: LedgerLegInput[] }
    | { stake: number; actualPayout: number },
  options?: { reSettle?: boolean },
): Promise<LedgerTicket> {
  const q = options?.reSettle ? "?reSettle=true" : "";
  return await apiFetch<LedgerTicket>(`/api/ledger/tickets/${encodeURIComponent(id)}${q}`, {
    method: "PATCH",
    json: body,
  });
}

export async function deleteLedgerTicket(id: string): Promise<void> {
  await apiFetch<void>(`/api/ledger/tickets/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}
