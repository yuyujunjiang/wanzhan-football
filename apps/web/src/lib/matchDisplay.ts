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

/** 返回本地化的「时:分」，绝不输出 Invalid Date */
export function formatKickoffClock(m: MatchLike): string {
  const t = (m.kickoffTime ?? "").trim();
  if (!t) return "--:--";
  if (/^\d{4}-\d{2}-\d{2}/.test(t)) {
    const parsed = new Date(t);
    if (Number.isNaN(parsed.getTime())) return "--:--";
    return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  if (!/^\d{1,2}:\d{2}(:\d{2})?$/.test(t)) return "--:--";
  const parsed = new Date(`${m.date}T${padTimePart(t)}`);
  if (Number.isNaN(parsed.getTime())) return "--:--";
  return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function parseKickoffLocal(m: MatchLike): Date | null {
  const t = (m.kickoffTime ?? "").trim();
  if (!t) return null;
  if (/^\d{4}-\d{2}-\d{2}/.test(t)) {
    const parsed = new Date(t);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  if (!/^\d{1,2}:\d{2}(:\d{2})?$/.test(t)) return null;
  const parsed = new Date(`${m.date}T${padTimePart(t)}`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export type MatchPhase = "not_started" | "live" | "finished";

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
  return "未开赛";
}
