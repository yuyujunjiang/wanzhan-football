"use client";

import { useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { WanzhanShell } from "../../../../../components/wanzhan/WanzhanShell";
import { listTicketsByDate, summarizeDay } from "../../../../../lib/wanzhanLedger";

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 12,
  } as const;
}

export default function WanzhanLedgerDayPage() {
  const params = useParams<{ date: string }>();
  const date = params.date;
  const search = useSearchParams();
  const initial = (search.get("filter") as "all" | "pending" | "settled" | null) ?? "all";
  const [filter, setFilter] = useState<"all" | "pending" | "settled">(initial);

  const summary = useMemo(() => summarizeDay(date), [date]);
  const list = useMemo(() => listTicketsByDate(date, filter), [date, filter]);

  return (
    <WanzhanShell
      title={`当天票 · ${date}`}
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
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "baseline" }}>
          <div style={{ fontWeight: 900 }}>统计</div>
          <a href="/wanzhan/ledger" style={{ color: "#1d39c4", fontSize: 13 }}>
            返回记账本 →
          </a>
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
            <div style={{ marginTop: 4, fontWeight: 900, color: summary.profit >= 0 ? "#135200" : "#b42318" }}>
              {summary.profit.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 12, ...cardStyle() }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
          <div style={{ fontWeight: 900 }}>票列表</div>
          <div style={{ display: "flex", gap: 8 }}>
            {(["all", "pending", "settled"] as const).map((f) => {
              const active = filter === f;
              const label = f === "all" ? "全部" : f === "pending" ? "待结" : "已结";
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
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

        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
          {list.map((t) => (
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
          {list.length === 0 ? <div style={{ fontSize: 13, color: "#666" }}>没有符合条件的票。</div> : null}
        </div>
      </div>
    </WanzhanShell>
  );
}

