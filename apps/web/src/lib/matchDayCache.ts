import { API_BASE_URL } from "./api";

export type MatchDayCache = {
  date: string;
  fixed: Record<string, unknown>[];
  dynamic?: Record<string, unknown>;
  meta?: Record<string, unknown>;
};

export const TODAY_RECOMMEND_LABEL = "今日推荐";

function formatLocalDateYYYYMMDD(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function todayDateString() {
  return formatLocalDateYYYYMMDD(new Date());
}

export async function fetchMatchDayCache(
  date = todayDateString()
): Promise<MatchDayCache> {
  const res = await fetch(
    `${API_BASE_URL}/api/matches/cache?date=${encodeURIComponent(date)}`
  );
  if (!res.ok) {
    throw new Error(`API ${res.status} /api/matches/cache`);
  }
  return (await res.json()) as MatchDayCache;
}

export function buildTodayRecommendApiContent(cache: MatchDayCache): string {
  return `${TODAY_RECOMMEND_LABEL}${JSON.stringify(cache)}`;
}
