"use client";

import { useMemo, useState } from "react";
import { WanzhanShell } from "../../../components/wanzhan/WanzhanShell";
import { listTicketsByDate, summarizeDay, summarizePeriod } from "../../../lib/wanzhanLedger";

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

type Mode = "day" | "week" | "month";

export default function WanzhanLedgerPage() {
  const [mode, setMode] = useState<Mode>("day");
  const [date, setDate] = useState(() => formatLocalDateYYYYMMDD(new Date()));

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

  const summary = useMemo(() => {
    if (mode === "day") return summarizeDay(date);
    return summarizePeriod(range.start, range.end);
  }, [date, mode, range.end, range.start]);

  const todayTickets = useMemo(() => listTicketsByDate(date, "all"), [date]);

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
                    border: `1px solid ${active ? "#cfe0ff" : "#eee"}`,
                    background: active ? "#f0f5ff" : "#fff",
                    color: active ? "#1d39c4" : "#111",
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
          待结 {summary.pendingCount} · 共 {summary.ticketCount} 张票
          {mode !== "day" ? ` · 区间 ${range.start} ~ ${range.end}` : ""}
        </div>
      </div>

      <div style={{ marginTop: 12, ...cardStyle() }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "baseline" }}>
          <div style={{ fontWeight: 800 }}>当天票</div>
          <a href={`/wanzhan/ledger/day/${encodeURIComponent(date)}`} style={{ color: "#1d39c4", fontSize: 13 }}>
            查看全部 →
          </a>
        </div>
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
          {todayTickets.slice(0, 3).map((t) => (
            <a
              key={t.id}
              href={`/tickets/${encodeURIComponent(t.id)}/report`}
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
                <div style={{ fontWeight: 750 }}>票 #{t.id.slice(0, 6)}</div>
                <div style={{ fontSize: 12, color: t.status === "pending" ? "#7a4f01" : "#135200" }}>
                  {t.status === "pending" ? "待结" : "已结"}
                </div>
              </div>
              <div style={{ marginTop: 6, fontSize: 12, color: "#666" }}>
                投入 {t.stake.toFixed(2)} · 回报 {t.payout.toFixed(2)} · 盈亏{" "}
                <span style={{ color: t.profit >= 0 ? "#135200" : "#b42318", fontWeight: 800 }}>
                  {t.profit.toFixed(2)}
                </span>
              </div>
            </a>
          ))}
          {todayTickets.length === 0 ? (
            <div style={{ fontSize: 13, color: "#666" }}>
              今天还没有记录。你可以在“赛程赛果”页点右下角 <b>+</b> 添加今天买的彩票。
            </div>
          ) : null}
        </div>
      </div>
    </WanzhanShell>
  );
}

