"use client";

import { useEffect, useMemo, useState } from "react";
import { WanzhanShell } from "../../../components/wanzhan/WanzhanShell";
import { StatStrip } from "../../../components/wanzhan/StatStrip";
import { API_BASE_URL } from "../../../lib/api";
import { deriveMatchPhase, formatKickoffClock, phaseLabel, type MatchPhase } from "../../../lib/matchDisplay";
import { summarizeDay } from "../../../lib/wanzhanLedger";

type MatchItem = {
  date: string;
  league: string;
  homeTeam: string;
  awayTeam: string;
  kickoffTime: string;
  matchKey: string;
  matchStatus?: string;
  finalScore?: string | null;
  halfScore?: string | null;
  goalLine?: string | null;
  had?: { h?: string; d?: string; a?: string } | null;
  hhad?: { goalLine?: string; h?: string; d?: string; a?: string } | null;
  outcomeSPF?: string;
  outcomeRQSPF?: string;
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

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 12,
  } as const;
}

function oddsGrid(label: string, odds: { h?: string; d?: string; a?: string } | null | undefined) {
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
        <div style={{ border: "1px solid #f1f1f1", borderRadius: 10, padding: "8px 10px" }}>
          <div style={{ fontSize: 11, color: "#666" }}>主胜</div>
          <div style={{ fontWeight: 750, marginTop: 4 }}>{odds?.h ?? "-"}</div>
        </div>
        <div style={{ border: "1px solid #f1f1f1", borderRadius: 10, padding: "8px 10px" }}>
          <div style={{ fontSize: 11, color: "#666" }}>平</div>
          <div style={{ fontWeight: 750, marginTop: 4 }}>{odds?.d ?? "-"}</div>
        </div>
        <div style={{ border: "1px solid #f1f1f1", borderRadius: 10, padding: "8px 10px" }}>
          <div style={{ fontSize: 11, color: "#666" }}>客胜</div>
          <div style={{ fontWeight: 750, marginTop: 4 }}>{odds?.a ?? "-"}</div>
        </div>
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

  const summary = useMemo(() => summarizeDay(today), [today]);

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
      const matches = body as MatchItem[];
      setDays([{ date: today, matchCount: matches.length, matches }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setDays([]);
    } finally {
      setLoading(false);
    }
  }

  /** 近 7 天赛果：不含今天；窗口为「今天-7」…「昨天」（与后端按天 JSON 缓存一致） */
  async function loadResultsWeek() {
    setLoading(true);
    setError(null);
    try {
      const start = addCalendarDays(today, -7);
      const res = await fetch(
        `${API_BASE_URL}/api/matches/range?start=${encodeURIComponent(start)}&days=7`,
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`API ${res.status} /api/matches/range${text ? `: ${text}` : ""}`);
      }
      const body = (await res.json()) as unknown;
      if (!Array.isArray(body)) throw new Error("matches response is not a list");
      const groups = body as MatchDayGroup[];
      const filtered = groups
        .filter((g) => g.date < today)
        .map((g) => ({
          ...g,
          matches: g.matches.filter((m) => m.finalScore != null && String(m.finalScore).trim() !== ""),
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

  useEffect(() => {
    if (view === "schedule") void loadSchedule();
    else void loadResultsWeek();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  useEffect(() => {
    if (view !== "schedule") return;
    const id = window.setInterval(() => void loadSchedule(), 60_000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, today]);

  useEffect(() => {
    if (view !== "schedule") return;
    const id = window.setInterval(() => setTick((n) => n + 1), 30_000);
    return () => window.clearInterval(id);
  }, [view]);

  const now = useMemo(() => new Date(), [tick]);

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
              {view === "schedule" ? `今日赛程 · ${today}` : "近 7 天已完赛（不含今日）"}
            </div>
            <button
              type="button"
              onClick={() => (view === "schedule" ? void loadSchedule() : void loadResultsWeek())}
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
              const phase: MatchPhase =
                view === "results" ? "finished" : deriveMatchPhase(m, now, day.date);
              const statusText = phaseLabel(phase);
              const scoreText =
                m.finalScore != null && String(m.finalScore).trim() !== ""
                  ? String(m.finalScore).trim()
                  : null;

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

                <div style={{ marginTop: 6, fontSize: 13, color: "#666" }}>
                  开赛时间：{formatKickoffClock(m)}
                </div>

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
                  {oddsGrid("胜平负 (HAD)", m.had)}
                  {oddsGrid(`让球胜平负 (HHAD) ${m.hhad?.goalLine ?? ""}`.trim(), m.hhad)}
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
              {view === "schedule" ? "今日没有返回任何比赛。" : "近 7 天内没有已完赛记录，或赛果尚未同步。"}
            </div>
          </div>
        ) : null}
      </div>
    </WanzhanShell>
  );
}

