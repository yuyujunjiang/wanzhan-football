export type TicketStatus = "pending" | "settled";

export type WanzhanTicket = {
  id: string;
  createdAt: string; // ISO
  date: string; // YYYY-MM-DD (local)
  status: TicketStatus;
  stake: number; // 投入
  payout: number; // 回报（可先为 0）
  profit: number; // payout - stake
  note?: string;
};

const STORAGE_KEY = "wanzhan_ledger_v1";

function safeParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function loadAll(): WanzhanTicket[] {
  if (typeof window === "undefined") return [];
  const data = safeParse<{ tickets: WanzhanTicket[] }>(window.localStorage.getItem(STORAGE_KEY));
  return Array.isArray(data?.tickets) ? data!.tickets : [];
}

function saveAll(tickets: WanzhanTicket[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ tickets }));
}

export function addTicket(input: {
  id: string;
  date: string;
  stake: number;
  payout: number;
  status: TicketStatus;
}) {
  const now = new Date().toISOString();
  const t: WanzhanTicket = {
    id: input.id,
    createdAt: now,
    date: input.date,
    stake: input.stake,
    payout: input.payout,
    status: input.status,
    profit: round2(input.payout - input.stake),
  };
  const all = loadAll();
  saveAll([t, ...all]);
}

export function listTicketsByDate(date: string, filter?: "all" | "pending" | "settled") {
  const all = loadAll().filter((t) => t.date === date);
  if (!filter || filter === "all") return all;
  return all.filter((t) => t.status === filter);
}

export function summarizeDay(date: string) {
  const list = listTicketsByDate(date, "all");
  const stake = sum(list.map((t) => t.stake));
  const payout = sum(list.map((t) => t.payout));
  const profit = round2(payout - stake);
  const pendingCount = list.filter((t) => t.status === "pending").length;
  return { stake, payout, profit, pendingCount, ticketCount: list.length };
}

export function summarizePeriod(startDate: string, endDate: string) {
  const all = loadAll().filter((t) => t.date >= startDate && t.date <= endDate);
  const stake = sum(all.map((t) => t.stake));
  const payout = sum(all.map((t) => t.payout));
  const profit = round2(payout - stake);
  const pendingCount = all.filter((t) => t.status === "pending").length;
  return { stake, payout, profit, pendingCount, ticketCount: all.length };
}

function sum(nums: number[]) {
  return nums.reduce((a, b) => a + (Number.isFinite(b) ? b : 0), 0);
}

function round2(n: number) {
  return Math.round(n * 100) / 100;
}

