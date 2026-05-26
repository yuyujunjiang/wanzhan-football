/** 竞彩赛程展示：开赛时间、阶段文案（替换 Selling 等英文状态） */

export type MatchLike = {
  date: string;
  kickoffTime: string;
  finalScore?: string | null;
  matchStatus?: string;
};

function padTimePart(t: string): string {
  const s = t.trim();
  if (/^\d{1,2}:\d{2}$/.test(s)) return `${s}:00`;
  return s;
}

/** 竞彩：销售日场次中，开球时刻 <=08:00 的仅有时分 → 下一自然日该时刻 */
function isEarlyKickoffTime(hours: number, minutes: number): boolean {
  return hours < 8 || (hours === 8 && minutes === 0);
}

function addCalendarDaysIso(isoDate: string, delta: number): string {
  const d = new Date(`${isoDate}T12:00:00`);
  d.setDate(d.getDate() + delta);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** 解析真实开球时刻（与后端 effective_kickoff_datetime 规则一致） */
export function effectiveKickoffLocal(m: MatchLike): Date | null {
  const t = (m.kickoffTime ?? "").trim();
  if (!t) return null;
  if (/^\d{4}-\d{2}-\d{2}/.test(t)) {
    const parsed = new Date(t);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  if (!/^\d{1,2}:\d{2}(:\d{2})?$/.test(t)) return null;
  const parts = padTimePart(t).split(":").map((x) => Number(x));
  const hours = parts[0] ?? 0;
  const minutes = parts[1] ?? 0;
  const seconds = parts[2] ?? 0;
  const calendarDate = isEarlyKickoffTime(hours, minutes)
    ? addCalendarDaysIso(m.date, 1)
    : m.date;
  const parsed = new Date(
    `${calendarDate}T${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`,
  );
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** 返回本地化的「时:分」，绝不输出 Invalid Date */
export function formatKickoffClock(m: MatchLike): string {
  const t = (m.kickoffTime ?? "").trim();
  if (!t) return "--:--";
  const ko = effectiveKickoffLocal(m);
  if (!ko) return "--:--";
  return ko.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function parseKickoffLocal(m: MatchLike): Date | null {
  return effectiveKickoffLocal(m);
}

export type MatchPhase = "not_started" | "live" | "finished" | "cancelled";

export type MatchWithPhase = MatchLike & { phase?: MatchPhase };

/** 赛程单日（通常为今日）：用比分 + 开赛时间推断阶段 */
export function deriveMatchPhase(m: MatchLike, now: Date, dayIso: string): MatchPhase {
  const fs = m.finalScore != null && String(m.finalScore).trim() !== "";
  if (fs) return "finished";

  const st = (m.matchStatus ?? "").trim();
  const stLower = st.toLowerCase();
  if (/^(完|结束|终场|全场)/.test(st)) return "finished";
  if (/^(end|full|ft)\b/i.test(stLower)) return "finished";

  if (m.date !== dayIso) return "not_started";

  const ko = parseKickoffLocal(m);
  if (!ko) {
    if (/^(进行|直播中|上半场|下半场)/.test(st)) return "live";
    return "not_started";
  }
  if (now.getTime() < ko.getTime()) return "not_started";
  return "live";
}

export function phaseLabel(phase: MatchPhase): string {
  if (phase === "finished") return "已完赛";
  if (phase === "live") return "已开赛";
  if (phase === "cancelled") return "推迟/取消";
  return "未开赛";
}

export function resolvePhase(m: MatchWithPhase, now: Date, dayIso: string): MatchPhase {
  if (m.phase) return m.phase;
  return deriveMatchPhase(m, now, dayIso);
}

export function isSchedulePhase(phase: MatchPhase): boolean {
  return phase === "not_started" || phase === "live";
}

export function isResultsPhase(phase: MatchPhase): boolean {
  return phase === "finished" || phase === "cancelled";
}
