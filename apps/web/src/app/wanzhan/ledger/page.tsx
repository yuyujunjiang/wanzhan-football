"use client";

import { useEffect, useMemo, useState } from "react";
import { WanzhanShell } from "../../../components/wanzhan/WanzhanShell";
import { getLedgerSummary, listLedgerTickets, type LedgerSummary, type LedgerTicket } from "../../../lib/api";

function formatLocalDateYYYYMMDD(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDays(date: string, delta: number) {
  const [y, m, d] = date.split("-").map((x) => Number(x));
  const dt = new Date(y, (m ?? 1) - 1, d ?? 1);
  dt.setDate(dt.getDate() + delta);
  return formatLocalDateYYYYMMDD(dt);
}

function startOfWeek(date: string) {
  const [y, m, d] = date.split("-").map((x) => Number(x));
  const dt = new Date(y, (m ?? 1) - 1, d ?? 1);
  const dow = dt.getDay() === 0 ? 7 : dt.getDay(); // 1..7
  dt.setDate(dt.getDate() - (dow - 1));
  return formatLocalDateYYYYMMDD(dt);
}

function startOfMonth(date: string) {
  const [y, m] = date.split("-").map((x) => Number(x));
  const dt = new Date(y, (m ?? 1) - 1, 1);
  return formatLocalDateYYYYMMDD(dt);
}

function endOfMonth(date: string) {
  const [y, m] = date.split("-").map((x) => Number(x));
  const dt = new Date(y, (m ?? 1), 0);
  return formatLocalDateYYYYMMDD(dt);
}

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 12,
  } as const;
}

function ticketTitle(ticket: LedgerTicket) {
  return ticket.legs.map((leg) => `${leg.homeTeam} vs ${leg.awayTeam} ${leg.selection}`);
}

type Mode = "day" | "week" | "month";

const EMPTY_SUMMARY: LedgerSummary = {
  stake: 0,
  payout: 0,
  profit: 0,
  pendingCount: 0,
  settledCount: 0,
  ticketCount: 0,
};

export default function WanzhanLedgerPage() {
  const [mode, setMode] = useState<Mode>("day");
  const [date, setDate] = useState(() => formatLocalDateYYYYMMDD(new Date()));
  const [summary, setSummary] = useState<LedgerSummary>(EMPTY_SUMMARY);
  const [tickets, setTickets] = useState<LedgerTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const range = useMemo(() => {
    if (mode === "day") return { start: date, end: date };
    if (mode === "week") {
      const start = startOfWeek(date);
      const end = addDays(start, 6);
      return { start, end };
    }
    const start = startOfMonth(date);
    const end = endOfMonth(date);
    return { start, end };
  }, [date, mode]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [nextSummary, nextTickets] = await Promise.all([
          getLedgerSummary(range.start, range.end),
          listLedgerTickets({ date, status: "all" }),
        ]);
        if (cancelled) return;
        setSummary(nextSummary);
        setTickets(nextTickets);
      } catch (err) {
        if (cancelled) return;
        setSummary(EMPTY_SUMMARY);
        setTickets([]);
        setError(err instanceof Error ? err.message : "记账数据加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [date, range.end, range.start]);

  return (
    <WanzhanShell
      title="记账本"
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
    >
      <div style={cardStyle()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
          <div style={{ fontWeight: 800 }}>统计</div>
          <div style={{ display: "flex", gap: 8 }}>
            {(["day", "week", "month"] as const).map((m) => {
              const active = mode === m;
              const label = m === "day" ? "日" : m === "week" ? "周" : "月";
              return (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  style={{
                    border: `1px solid ${active ? "#bbb" : "#eee"}`,
                    background: active ? "#f5f5f5" : "#fff",
                    color: "#111",
                    padding: "8px 10px",
                    borderRadius: 999,
                    fontSize: 13,
                    fontWeight: 750,
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ marginTop: 10, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ color: "#666", fontSize: 13 }}>{mode === "day" ? "选择日期" : "选择任意日期（用于定位周/月）"}</div>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.currentTarget.value)}
            style={{
              border: "1px solid #ddd",
              borderRadius: 10,
              padding: "8px 10px",
              fontSize: 14,
              background: "#fff",
            }}
          />
        </div>

        <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 12, color: "#666" }}>投入</div>
            <div style={{ marginTop: 4, fontWeight: 800 }}>{summary.stake.toFixed(2)}</div>
          </div>
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 12, color: "#666" }}>回报</div>
            <div style={{ marginTop: 4, fontWeight: 800 }}>{summary.payout.toFixed(2)}</div>
          </div>
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 12, color: "#666" }}>盈亏</div>
            <div
              style={{
                marginTop: 4,
                fontWeight: 900,
                color: summary.profit >= 0 ? "#135200" : "#b42318",
              }}
            >
              {summary.profit.toFixed(2)}
            </div>
          </div>
        </div>

        <div style={{ marginTop: 10, fontSize: 12, color: "#666" }}>
          {loading ? "加载中 · " : ""}
          待结 {summary.pendingCount} · 共 {summary.ticketCount} 张票
          {mode !== "day" ? ` · 区间 ${range.start} ~ ${range.end}` : ""}
        </div>
        {error ? <div style={{ marginTop: 8, fontSize: 12, color: "#b42318" }}>{error}</div> : null}
      </div>

      <div style={{ marginTop: 12, ...cardStyle() }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "baseline" }}>
          <div style={{ fontWeight: 800 }}>当天票</div>
          <a href={`/wanzhan/ledger/day/${encodeURIComponent(date)}`} style={{ color: "#444", fontSize: 13 }}>
            查看全部 →
          </a>
        </div>
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
          {tickets.slice(0, 3).map((t) => {
            const titleLines = ticketTitle(t);
            return (
              <a
                key={t.id}
                href={`/wanzhan/ledger/tickets/${encodeURIComponent(t.id)}`}
                style={{
                  textDecoration: "none",
                  color: "#111",
                  border: "1px solid #eee",
                  borderRadius: 12,
                  padding: 10,
                  background: "#fff",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <div style={{ fontWeight: 750, lineHeight: 1.5 }}>
                    {titleLines.map((line) => (
                      <div key={line}>{line}</div>
                    ))}
                  </div>
                  <div style={{ fontSize: 12, color: t.status === "pending" ? "#7a4f01" : "#135200" }}>
                    {t.status === "pending" ? "待结" : "已结"}
                  </div>
                </div>
                <div style={{ marginTop: 6, fontSize: 12, color: "#666" }}>
                  {t.status === "pending" ? (
                    <>投入 {t.stake.toFixed(2)} · 预计回报 {t.estimatedPayout.toFixed(2)}</>
                  ) : (
                    <>
                      投入 {t.stake.toFixed(2)} · 回报 {t.actualPayout.toFixed(2)} · 盈亏{" "}
                      <span style={{ color: t.profit >= 0 ? "#135200" : "#b42318", fontWeight: 800 }}>
                        {t.profit.toFixed(2)}
                      </span>
                    </>
                  )}
                </div>
              </a>
            );
          })}
          {!loading && tickets.length === 0 ? (
            <div style={{ fontSize: 13, color: "#666" }}>
              今天还没有记录。你可以在“赛程赛果”页点右下角 <b>+</b> 添加今天买的彩票。
            </div>
          ) : null}
        </div>
      </div>
    </WanzhanShell>
  );
}
