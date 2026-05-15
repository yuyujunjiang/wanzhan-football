"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { WanzhanShell } from "../../../../../components/wanzhan/WanzhanShell";
import {
  deleteLedgerTicket,
  getLedgerSummary,
  listLedgerTickets,
  type LedgerSummary,
  type LedgerTicket,
} from "../../../../../lib/api";

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 12,
  } as const;
}

function selectionColor(selection: string) {
  if (selection === "胜" || selection === "让胜") return "#cf1322";
  if (selection === "负" || selection === "让负") return "#237804";
  return "#111";
}

function TicketTitle({ ticket }: { ticket: LedgerTicket }) {
  return (
    <div style={{ display: "grid", gap: 2, lineHeight: 1.45 }}>
      {ticket.legs.map((leg) => (
        <div
          key={leg.id}
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr) 44px",
            columnGap: 10,
            alignItems: "baseline",
          }}
        >
          <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {leg.homeTeam} vs {leg.awayTeam}
          </span>
          <span style={{ color: selectionColor(leg.selection), fontWeight: 900, textAlign: "right" }}>
            {leg.selection}
          </span>
        </div>
      ))}
    </div>
  );
}

const EMPTY_SUMMARY: LedgerSummary = {
  stake: 0,
  payout: 0,
  profit: 0,
  pendingCount: 0,
  settledCount: 0,
  ticketCount: 0,
};

const FILTERS = ["all", "pending", "settled"] as const;
type Filter = (typeof FILTERS)[number];

function parseFilter(value: string | null): Filter {
  return FILTERS.includes(value as Filter) ? (value as Filter) : "all";
}

export default function WanzhanLedgerDayPage() {
  const params = useParams<{ date: string }>();
  const date = params.date;
  const search = useSearchParams();
  const initial = parseFilter(search.get("filter"));
  const [filter, setFilter] = useState<Filter>(initial);
  const [summary, setSummary] = useState<LedgerSummary>(EMPTY_SUMMARY);
  const [list, setList] = useState<LedgerTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [nextSummary, nextList] = await Promise.all([
          getLedgerSummary(date, date),
          listLedgerTickets({ date, status: filter }),
        ]);
        if (cancelled) return;
        setSummary(nextSummary);
        setList(nextList);
      } catch (err) {
        if (cancelled) return;
        setSummary(EMPTY_SUMMARY);
        setList([]);
        setError(err instanceof Error ? err.message : "记账数据加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [date, filter]);

  async function onDeleteTicket(t: LedgerTicket) {
    if (!window.confirm("确定删除这张票？")) return;
    try {
      await deleteLedgerTicket(t.id);
      const [nextSummary, nextList] = await Promise.all([
        getLedgerSummary(date, date),
        listLedgerTickets({ date, status: filter }),
      ]);
      setSummary(nextSummary);
      setList(nextList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  }

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
          <a href="/wanzhan/ledger" style={{ color: "#444", fontSize: 13 }}>
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
        <div style={{ marginTop: 10, fontSize: 12, color: "#666" }}>
          {loading ? "加载中 · " : ""}待结 {summary.pendingCount} · 已结 {summary.settledCount} · 共 {summary.ticketCount} 张票
        </div>
        {error ? <div style={{ marginTop: 8, fontSize: 12, color: "#b42318" }}>{error}</div> : null}
      </div>

      <div style={{ marginTop: 12, ...cardStyle() }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
          <div style={{ fontWeight: 900 }}>票列表</div>
          <div style={{ display: "flex", gap: 8 }}>
            {FILTERS.map((f) => {
              const active = filter === f;
              const label = f === "all" ? "全部" : f === "pending" ? "待结" : "已结";
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
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

        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
          {list.map((t) => {
            return (
              <div
                key={t.id}
                style={{
                  border: "1px solid #eee",
                  borderRadius: 12,
                  padding: 10,
                  background: "#fff",
                }}
              >
                <a
                  href={`/wanzhan/ledger/tickets/${encodeURIComponent(t.id)}`}
                  style={{ textDecoration: "none", color: "#111", display: "block" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                    <div style={{ flex: 1, minWidth: 0, fontWeight: 750 }}>
                      <TicketTitle ticket={t} />
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
                <div
                  style={{
                    marginTop: 10,
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: 8,
                    borderTop: "1px solid #f0f0f0",
                    paddingTop: 10,
                  }}
                >
                  <a
                    href={`/wanzhan/ledger/tickets/${encodeURIComponent(t.id)}/edit`}
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: "#1d39c4",
                      textDecoration: "none",
                    }}
                  >
                    编辑
                  </a>
                  <button
                    type="button"
                    onClick={() => void onDeleteTicket(t)}
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: "#b42318",
                      background: "none",
                      border: "none",
                      padding: 0,
                      cursor: "pointer",
                    }}
                  >
                    删除
                  </button>
                </div>
              </div>
            );
          })}
          {!loading && list.length === 0 ? <div style={{ fontSize: 13, color: "#666" }}>没有符合条件的票。</div> : null}
        </div>
      </div>
    </WanzhanShell>
  );
}
