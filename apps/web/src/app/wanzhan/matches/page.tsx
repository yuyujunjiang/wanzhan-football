"use client";

import { useEffect, useMemo, useState } from "react";
import { WanzhanShell } from "../../../components/wanzhan/WanzhanShell";
import { StatStrip } from "../../../components/wanzhan/StatStrip";
import { API_BASE_URL, createLedgerTicket, getLedgerSummary, type LedgerSummary } from "../../../lib/api";
import { computeEstimatedPayout, computeStake } from "../../../lib/ledgerMath";
import {
  formatKickoffClock,
  isResultsPhase,
  isSchedulePhase,
  phaseLabel,
  resolvePhase,
  type MatchPhase,
} from "../../../lib/matchDisplay";

type MatchItem = {
  date: string;
  league: string;
  homeTeam: string;
  awayTeam: string;
  kickoffTime: string;
  matchKey: string;
  matchId?: number | null;
  matchStatus?: string;
  finalScore?: string | null;
  halfScore?: string | null;
  goalLine?: string | null;
  had?: { h?: string; d?: string; a?: string } | null;
  hhad?: { goalLine?: string; h?: string; d?: string; a?: string } | null;
  outcomeSPF?: string;
  outcomeRQSPF?: string;
  phase?: MatchPhase;
};

type MatchDayGroup = {
  date: string;
  matchCount: number;
  matches: MatchItem[];
};

function formatLocalDateYYYYMMDD(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function weekdayLabel(date: string) {
  const d = new Date(`${date}T00:00:00`);
  const w = ["日", "一", "二", "三", "四", "五", "六"][d.getDay()];
  return `周${w}`;
}

function addCalendarDays(isoDate: string, delta: number): string {
  const d = new Date(`${isoDate}T12:00:00`);
  d.setDate(d.getDate() + delta);
  return formatLocalDateYYYYMMDD(d);
}

type ViewMode = "schedule" | "results";
type PlayType = "SPF" | "RQSPF";

type SelectedLeg = {
  date: string;
  matchKey: string;
  matchId?: number | null;
  league: string;
  homeTeam: string;
  awayTeam: string;
  kickoffTime?: string | null;
  playType: PlayType;
  selection: string;
  sp: number;
  handicap?: number | null;
};

function parseOdd(value: unknown) {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) && n > 1 ? n : null;
}

/** 补记模式无赔率时用占位 SP，仅用于估算奖金展示；结算以官方赛果为准。 */
const RESULTS_MAKEUP_PLACEHOLDER_SP = 2;

function spForTicket(view: ViewMode, spValue: unknown): number | null {
  const parsed = parseOdd(spValue);
  if (view === "results") return parsed ?? RESULTS_MAKEUP_PLACEHOLDER_SP;
  return parsed;
}

function parseHandicap(value: unknown) {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatSelectedKickoff(kickoffTime?: string | null) {
  const t = (kickoffTime ?? "").trim();
  if (!t) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(t)) {
    const parsed = new Date(t);
    return Number.isNaN(parsed.getTime())
      ? t
      : parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return t.replace(/:00$/, "");
}

function selectedKey(matchKey: string) {
  return matchKey;
}

const EMPTY_LEDGER_SUMMARY: LedgerSummary = {
  stake: 0,
  payout: 0,
  profit: 0,
  pendingCount: 0,
  settledCount: 0,
  ticketCount: 0,
};

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 12,
  } as const;
}

function oddsButtonStyle(active: boolean, disabled: boolean) {
  return {
    border: active ? "1px solid #111" : "1px solid #eee",
    borderRadius: 10,
    padding: "8px 10px",
    background: active ? "#111" : disabled ? "#f7f7f7" : "#fff",
    color: active ? "#fff" : disabled ? "#aaa" : "#111",
    textAlign: "left",
    cursor: disabled ? "not-allowed" : "pointer",
    minWidth: 0,
  } as const;
}

function OddsOptionButton({
  title,
  value,
  active,
  onClick,
  bettingLocked = false,
  resultsMakeup = false,
}: {
  title: string;
  value?: string;
  active: boolean;
  onClick: () => void;
  bettingLocked?: boolean;
  resultsMakeup?: boolean;
}) {
  const hasOdd = parseOdd(value) != null;
  const disabled = bettingLocked || (!resultsMakeup && !hasOdd);
  const displayValue = resultsMakeup && !hasOdd ? "—" : (value ?? "-");
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={disabled ? undefined : onClick}
      style={oddsButtonStyle(active, disabled)}
    >
      <div style={{ fontSize: 11, color: active ? "#ddd" : disabled ? "#aaa" : "#666" }}>{title}</div>
      <div style={{ fontWeight: 750, marginTop: 4 }}>{displayValue}</div>
    </button>
  );
}

function oddsGrid({
  label,
  options,
  bettingLocked = false,
  resultsMakeup = false,
}: {
  label: string;
  options: {
    title: string;
    value?: string;
    active: boolean;
    onClick: () => void;
  }[];
  bettingLocked?: boolean;
  resultsMakeup?: boolean;
}) {
  return (
    <div
      style={{
        border: "1px solid #eee",
        borderRadius: 12,
        padding: 10,
        background: "#fff",
      }}
    >
      <div style={{ fontSize: 12, color: "#666", display: "flex", justifyContent: "space-between" }}>
        <span>{label}</span>
      </div>
      <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {options.map((option) => (
          <OddsOptionButton
            key={option.title}
            {...option}
            bettingLocked={bettingLocked}
            resultsMakeup={resultsMakeup}
          />
        ))}
      </div>
    </div>
  );
}

export default function WanzhanMatchesPage() {
  const [view, setView] = useState<ViewMode>("schedule");
  const today = formatLocalDateYYYYMMDD(new Date());
  const [tick, setTick] = useState(0);

  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState<MatchDayGroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Record<string, SelectedLeg>>({});
  const [ticketOpen, setTicketOpen] = useState(false);
  const [multiplier, setMultiplier] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [summary, setSummary] = useState<LedgerSummary>(EMPTY_LEDGER_SUMMARY);

  const selectedLegs = useMemo(() => Object.values(selected), [selected]);
  const ticketMode = view === "results" ? "results" : "schedule";
  const ticketTitleId = "wanzhan-ticket-confirm-title";

  async function loadLedgerSummary() {
    try {
      const next = await getLedgerSummary(today, today);
      setSummary(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setSummary(EMPTY_LEDGER_SUMMARY);
    }
  }

  async function loadSchedule() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/matches?date=${encodeURIComponent(today)}`);
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`API ${res.status} /api/matches${text ? `: ${text}` : ""}`);
      }
      const body = (await res.json()) as unknown;
      if (!Array.isArray(body)) throw new Error("matches response is not a list");
      const matches = (body as MatchItem[]).filter((m) =>
        isSchedulePhase(resolvePhase(m, new Date(), today)),
      );
      setDays([{ date: today, matchCount: matches.length, matches }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setDays([]);
    } finally {
      setLoading(false);
    }
  }

  async function fetchCompletedMatches(date: string): Promise<MatchItem[]> {
    const res = await fetch(`${API_BASE_URL}/api/matches?date=${encodeURIComponent(date)}`);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API ${res.status} /api/matches${text ? `: ${text}` : ""}`);
    }
    const body = (await res.json()) as unknown;
    if (!Array.isArray(body)) throw new Error("matches response is not a list");
    return (body as MatchItem[]).filter((m) =>
      isResultsPhase(resolvePhase(m, new Date(), date)),
    );
  }

  async function loadResultsHistory() {
    setLoading(true);
    setError(null);
    try {
      const start = addCalendarDays(today, -7);
      const res = await fetch(
        `${API_BASE_URL}/api/matches/range?start=${encodeURIComponent(start)}&days=8`,
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`API ${res.status} /api/matches/range${text ? `: ${text}` : ""}`);
      }
      const body = (await res.json()) as unknown;
      if (!Array.isArray(body)) throw new Error("matches response is not a list");
      const groups = body as MatchDayGroup[];
      const filtered = groups
        .filter((g) => g.date <= today)
        .map((g) => ({
          ...g,
          matches: g.matches.filter((m) => isResultsPhase(resolvePhase(m, new Date(), g.date))),
        }))
        .filter((g) => g.matches.length > 0)
        .sort((a, b) => (a.date < b.date ? 1 : -1));
      setDays(filtered.map((g) => ({ ...g, matchCount: g.matches.length })));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setDays([]);
    } finally {
      setLoading(false);
    }
  }

  async function refreshTodayResults() {
    try {
      const matches = await fetchCompletedMatches(today);
      setDays((current) => {
        const rest = current.filter((g) => g.date !== today);
        if (matches.length === 0) return rest;
        return [{ date: today, matchCount: matches.length, matches }, ...rest].sort((a, b) =>
          a.date < b.date ? 1 : -1,
        );
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    setSelected({});
    setTicketOpen(false);
    if (view === "schedule") void loadSchedule();
    else void loadResultsHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  useEffect(() => {
    void loadLedgerSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [today]);

  useEffect(() => {
    if (view !== "schedule") return;
    const id = window.setInterval(() => void loadSchedule(), 60_000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, today]);

  useEffect(() => {
    if (view !== "results") return;
    const id = window.setInterval(() => void refreshTodayResults(), 300_000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, today]);

  useEffect(() => {
    if (view !== "schedule") return;
    const id = window.setInterval(() => setTick((n) => n + 1), 30_000);
    return () => window.clearInterval(id);
  }, [view]);

  const now = useMemo(() => new Date(), [tick]);

  useEffect(() => {
    if (view !== "schedule") return;
    setSelected((current) => {
      const allMatches = days.flatMap((d) =>
        d.matches.map((m) => ({ m, day: d.date })),
      );
      let changed = false;
      const next = { ...current };
      for (const [key, leg] of Object.entries(current)) {
        const row = allMatches.find((x) => x.m.matchKey === leg.matchKey);
        if (!row) continue;
        const phase = resolvePhase(row.m, now, row.day);
        if (phase !== "not_started") {
          delete next[key];
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [days, now, view]);

  function toggleLeg(
    match: MatchItem,
    matchDate: string,
    playType: PlayType,
    selection: string,
    spValue: unknown,
    handicap?: number | null,
  ) {
    const sp = spForTicket(view, spValue);
    if (sp == null) return;
    if (view === "schedule" && resolvePhase(match, now, matchDate) !== "not_started") {
      return;
    }
    const key = selectedKey(match.matchKey);
    setSelected((current) => {
      const existing = current[key];
      if (existing?.playType === playType && existing.selection === selection) {
        const next = { ...current };
        delete next[key];
        return next;
      }

      return {
        ...current,
        [key]: {
          date: matchDate,
          matchKey: match.matchKey,
          matchId: match.matchId,
          league: match.league,
          homeTeam: match.homeTeam,
          awayTeam: match.awayTeam,
          kickoffTime: match.kickoffTime,
          playType,
          selection,
          sp,
          handicap,
        },
      };
    });
  }

  async function submitTicket() {
    if (selectedLegs.length === 0 || submitting) return;
    const ticketDate = selectedLegs[0]?.date ?? today;
    if (selectedLegs.some((leg) => leg.date !== ticketDate)) {
      setError("不能混合不同日期的比赛。");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const legs = selectedLegs.map(({ date: _date, ...leg }) => leg);
      await createLedgerTicket({ mode: ticketMode, date: ticketDate, multiplier, legs });
      setSelected({});
      setTicketOpen(false);
      setMultiplier(1);
      if (view === "schedule") await loadSchedule();
                else await loadResultsHistory();
      await loadLedgerSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <WanzhanShell
      title="赛程赛果"
      right={
        <a
          href="/upload"
          style={{
            border: "1px solid #111",
            background: "#111",
            color: "#fff",
            padding: "8px 10px",
            borderRadius: 12,
            fontSize: 13,
            fontWeight: 750,
            textDecoration: "none",
            whiteSpace: "nowrap",
          }}
        >
          添加彩票
        </a>
      }
      top={
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <button
              type="button"
              onClick={() => setView("schedule")}
              style={{
                border: view === "schedule" ? "1px solid #111" : "1px solid #ddd",
                background: view === "schedule" ? "#111" : "#fff",
                color: view === "schedule" ? "#fff" : "#111",
                padding: "10px 12px",
                borderRadius: 12,
                fontSize: 15,
                fontWeight: 700,
              }}
            >
              赛程
            </button>
            <button
              type="button"
              onClick={() => setView("results")}
              style={{
                border: view === "results" ? "1px solid #111" : "1px solid #ddd",
                background: view === "results" ? "#111" : "#fff",
                color: view === "results" ? "#fff" : "#111",
                padding: "10px 12px",
                borderRadius: 12,
                fontSize: 15,
                fontWeight: 700,
              }}
            >
              赛果
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
            <div style={{ color: "#666", fontSize: 13 }}>
              {view === "schedule" ? `今日赛程 · ${today}` : "近 7 天赛果"}
            </div>
            <button
              type="button"
              onClick={() => {
                if (view === "schedule") void loadSchedule();
                else void loadResultsHistory();
                void loadLedgerSummary();
              }}
              style={{
                border: "1px solid #ddd",
                background: "#fff",
                padding: "8px 10px",
                borderRadius: 10,
                fontSize: 14,
              }}
            >
              刷新
            </button>
          </div>

          <StatStrip
            profitToday={summary.ticketCount ? summary.profit : 0}
            pendingCount={summary.pendingCount}
            onOpenTodayTickets={() => (window.location.href = `/wanzhan/ledger/day/${encodeURIComponent(today)}`)}
            onOpenPendingTickets={() =>
              (window.location.href = `/wanzhan/ledger/day/${encodeURIComponent(today)}?filter=pending`)
            }
          />
        </div>
      }
    >
      {loading ? <div style={{ marginTop: 12, color: "#666", fontSize: 14 }}>加载中...</div> : null}

      {error ? (
        <div
          style={{
            marginTop: 12,
            background: "#fff",
            border: "1px solid #f1c0c0",
            color: "#b42318",
            borderRadius: 14,
            padding: 12,
            fontSize: 13,
            whiteSpace: "pre-wrap",
          }}
        >
          {error}
        </div>
      ) : null}

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 14 }}>
        {days.map((day) => (
          <div key={day.date} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div style={{ fontSize: 13, color: "#666" }}>
                {weekdayLabel(day.date)} {day.date}
              </div>
              <div style={{ fontSize: 13, color: "#666" }}>共 {day.matchCount} 场</div>
            </div>

            {day.matches.map((m) => {
              const phase = resolvePhase(m, now, day.date);
              const bettingLocked = view === "schedule" && phase !== "not_started";
              const statusText = phaseLabel(phase);
              const scoreText =
                m.finalScore != null && String(m.finalScore).trim() !== ""
                  ? String(m.finalScore).trim()
                  : null;
              const kickoffClock = formatKickoffClock(m);
              const activeLeg = selected[selectedKey(m.matchKey)];
              const hhadHandicap = parseHandicap(m.hhad?.goalLine ?? m.goalLine);
              const resultsMakeup = view === "results";

              return (
              <div key={`${day.date}-${m.matchKey}`} style={cardStyle()}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                  <div style={{ fontWeight: 650 }}>{m.league}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                    {scoreText ? (
                      <div style={{ fontSize: 15, fontWeight: 800 }}>{scoreText}</div>
                    ) : phase === "live" ? (
                      <div style={{ fontSize: 13, color: "#888" }}>—</div>
                    ) : null}
                    <div
                      style={{
                        fontSize: 12,
                        padding: "2px 8px",
                        borderRadius: 999,
                        border: "1px solid #eee",
                        color: "#333",
                        background: "#f5f5f5",
                        fontWeight: 650,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {statusText}
                    </div>
                  </div>
                </div>

                {kickoffClock !== "--:--" ? (
                  <div style={{ marginTop: 6, fontSize: 13, color: "#666" }}>
                    开赛时间：{kickoffClock}
                  </div>
                ) : null}

                <div style={{ marginTop: 8, fontSize: 16, fontWeight: 800 }}>
                  {m.homeTeam} <span style={{ color: "#999" }}>vs</span> {m.awayTeam}
                </div>

                <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {m.halfScore ? (
                    <div
                      style={{
                        fontSize: 12,
                        padding: "4px 10px",
                        borderRadius: 999,
                        border: "1px solid #eee",
                        background: "#fafafa",
                        color: "#444",
                      }}
                    >
                      半场 {m.halfScore}
                    </div>
                  ) : null}
                  {m.goalLine ? (
                    <div
                      style={{
                        fontSize: 12,
                        padding: "4px 10px",
                        borderRadius: 999,
                        border: "1px solid #eee",
                        background: "#fafafa",
                        color: "#444",
                      }}
                    >
                      让球 {m.goalLine}
                    </div>
                  ) : null}
                </div>

                {view === "results" && (m.outcomeSPF || m.outcomeRQSPF) ? (
                  <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10, background: "#fff" }}>
                      <div style={{ fontSize: 12, color: "#666" }}>赛果 SPF</div>
                      <div style={{ marginTop: 4, fontWeight: 650 }}>{m.outcomeSPF ?? "-"}</div>
                    </div>
                    <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10, background: "#fff" }}>
                      <div style={{ fontSize: 12, color: "#666" }}>赛果 RQSPF</div>
                      <div style={{ marginTop: 4, fontWeight: 650 }}>{m.outcomeRQSPF ?? "-"}</div>
                    </div>
                  </div>
                ) : null}

                <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
                  {oddsGrid({
                    bettingLocked,
                    resultsMakeup,
                    label: "胜平负",
                    options: [
                      {
                        title: "主胜",
                        value: m.had?.h,
                        active: activeLeg?.playType === "SPF" && activeLeg.selection === "胜",
                        onClick: () => toggleLeg(m, day.date, "SPF", "胜", m.had?.h, null),
                      },
                      {
                        title: "平",
                        value: m.had?.d,
                        active: activeLeg?.playType === "SPF" && activeLeg.selection === "平",
                        onClick: () => toggleLeg(m, day.date, "SPF", "平", m.had?.d, null),
                      },
                      {
                        title: "客胜",
                        value: m.had?.a,
                        active: activeLeg?.playType === "SPF" && activeLeg.selection === "负",
                        onClick: () => toggleLeg(m, day.date, "SPF", "负", m.had?.a, null),
                      },
                    ],
                  })}
                  {oddsGrid({
                    bettingLocked,
                    resultsMakeup,
                    label: "让球胜平负",
                    options: [
                      {
                        title: "让胜",
                        value: m.hhad?.h,
                        active: activeLeg?.playType === "RQSPF" && activeLeg.selection === "让胜",
                        onClick: () => toggleLeg(m, day.date, "RQSPF", "让胜", m.hhad?.h, hhadHandicap),
                      },
                      {
                        title: "让平",
                        value: m.hhad?.d,
                        active: activeLeg?.playType === "RQSPF" && activeLeg.selection === "让平",
                        onClick: () => toggleLeg(m, day.date, "RQSPF", "让平", m.hhad?.d, hhadHandicap),
                      },
                      {
                        title: "让负",
                        value: m.hhad?.a,
                        active: activeLeg?.playType === "RQSPF" && activeLeg.selection === "让负",
                        onClick: () => toggleLeg(m, day.date, "RQSPF", "让负", m.hhad?.a, hhadHandicap),
                      },
                    ],
                  })}
                </div>
              </div>
              );
            })}

            {!loading && !error && day.matches.length === 0 ? (
              <div style={cardStyle()}>
                <div style={{ fontWeight: 650, marginBottom: 6 }}>暂无比赛</div>
                <div style={{ color: "#666", fontSize: 13 }}>该日期没有返回任何比赛。</div>
              </div>
            ) : null}
          </div>
        ))}

        {!loading && !error && days.length === 0 ? (
          <div style={cardStyle()}>
            <div style={{ fontWeight: 650, marginBottom: 6 }}>{view === "schedule" ? "暂无赛程" : "暂无赛果"}</div>
            <div style={{ color: "#666", fontSize: 13 }}>
              {view === "schedule" ? "今日没有返回任何比赛。" : "近 7 天暂无已完赛记录，或赛果尚未同步。"}
            </div>
          </div>
        ) : null}
      </div>
      {selectedLegs.length > 0 ? (
        <button
          type="button"
          onClick={() => setTicketOpen(true)}
          style={{
            position: "fixed",
            right: 18,
            bottom: 18,
            zIndex: 40,
            border: "1px solid #111",
            background: "#111",
            color: "#fff",
            borderRadius: 999,
            padding: "12px 18px",
            fontSize: 15,
            fontWeight: 800,
            boxShadow: "0 12px 28px rgba(0,0,0,0.18)",
          }}
        >
          {ticketMode === "results" ? "补记" : "出票"} · {selectedLegs.length}场
        </button>
      ) : null}

      {ticketOpen ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            background: "rgba(0,0,0,0.28)",
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            padding: 14,
          }}
          onClick={() => {
            if (!submitting) setTicketOpen(false);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={ticketTitleId}
            style={{
              width: "100%",
              maxWidth: 560,
              background: "#fff",
              border: "1px solid #e6e6e6",
              borderRadius: 16,
              padding: 14,
              boxShadow: "0 18px 45px rgba(0,0,0,0.2)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
              <div id={ticketTitleId} style={{ fontSize: 16, fontWeight: 800 }}>
                {ticketMode === "results" ? "补记" : "出票"} · {selectedLegs.length}x1
              </div>
              <button
                type="button"
                aria-label="关闭"
                disabled={submitting}
                onClick={() => setTicketOpen(false)}
                style={{
                  border: "1px solid #eee",
                  background: "#fff",
                  borderRadius: 999,
                  width: 32,
                  height: 32,
                  fontSize: 18,
                  lineHeight: "28px",
                  color: "#333",
                }}
              >
                ×
              </button>
            </div>

            <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8, maxHeight: "42vh", overflow: "auto" }}>
              {selectedLegs.map((leg) => (
                <div
                  key={leg.matchKey}
                  style={{
                    border: "1px solid #eee",
                    borderRadius: 12,
                    padding: 10,
                    background: "#fafafa",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color: "#666",
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 8,
                    }}
                  >
                    <span>{leg.league}</span>
                    <span>{formatSelectedKickoff(leg.kickoffTime)}</span>
                  </div>
                  <div style={{ marginTop: 5, fontWeight: 750 }}>
                    {leg.homeTeam} <span style={{ color: "#999" }}>vs</span> {leg.awayTeam}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 13, color: "#333" }}>
                    {leg.playType} · {leg.selection}
                    {leg.handicap != null ? ` (${leg.handicap > 0 ? "+" : ""}${leg.handicap})` : ""} · {leg.sp.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                <div style={{ fontSize: 12, color: "#666" }}>倍数</div>
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={multiplier}
                  onChange={(e) => setMultiplier(Math.max(1, Math.floor(Number(e.target.value) || 1)))}
                  style={{
                    marginTop: 6,
                    width: "100%",
                    border: "1px solid #ddd",
                    borderRadius: 10,
                    padding: "8px 10px",
                    fontSize: 16,
                    fontWeight: 750,
                    boxSizing: "border-box",
                  }}
                />
              </div>
              <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                <div style={{ fontSize: 12, color: "#666" }}>过关</div>
                <div style={{ marginTop: 8, fontSize: 16, fontWeight: 800 }}>{selectedLegs.length}x1</div>
              </div>
              <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                <div style={{ fontSize: 12, color: "#666" }}>投注</div>
                <div style={{ marginTop: 8, fontSize: 16, fontWeight: 800 }}>¥{computeStake(multiplier).toFixed(2)}</div>
              </div>
              <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
                <div style={{ fontSize: 12, color: "#666" }}>预计</div>
                <div style={{ marginTop: 8, fontSize: 16, fontWeight: 800 }}>
                  ¥{computeEstimatedPayout(selectedLegs.map((l) => l.sp), multiplier).toFixed(2)}
                </div>
              </div>
            </div>

            <button
              type="button"
              disabled={submitting || selectedLegs.length === 0}
              onClick={() => void submitTicket()}
              style={{
                marginTop: 12,
                width: "100%",
                border: "1px solid #111",
                background: submitting ? "#555" : "#111",
                color: "#fff",
                borderRadius: 12,
                padding: "12px 14px",
                fontSize: 15,
                fontWeight: 800,
              }}
            >
              {submitting ? "提交中..." : ticketMode === "results" ? "确认补记" : "确认出票"}
            </button>
          </div>
        </div>
      ) : null}
    </WanzhanShell>
  );
}
