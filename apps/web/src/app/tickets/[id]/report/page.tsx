"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { WanzhanShell } from "../../../../components/wanzhan/WanzhanShell";
import { getTicket, type Ticket } from "../../../../lib/api";
import { addTicket } from "../../../../lib/wanzhanLedger";

type PayoutReport = {
  status: "won" | "lost" | "pending" | "partial";
  totalPayout: number;
  details?: { legHits?: boolean[] } | Record<string, unknown>;
  unmatchedLegs: string[];
};

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 12,
  } as const;
}

function statusMeta(status: PayoutReport["status"]) {
  switch (status) {
    case "won":
      return { label: "已中奖", color: "#135200", border: "#b7eb8f", bg: "#f6ffed" };
    case "lost":
      return { label: "未中奖", color: "#b42318", border: "#f1c0c0", bg: "#fff1f0" };
    case "partial":
      return { label: "部分结果", color: "#7a4f01", border: "#ffe58f", bg: "#fffbe6" };
    case "pending":
    default:
      return { label: "待定", color: "#1d39c4", border: "#adc6ff", bg: "#f0f5ff" };
  }
}

function formatMoney(n: number) {
  if (!Number.isFinite(n)) return "-";
  return n.toFixed(2);
}

export default function TicketReportPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [loading, setLoading] = useState(true);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [report, setReport] = useState<PayoutReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getTicket(id);
        if (cancelled) return;
        setTicket(res.ticket);
        setReport((res.report ?? null) as PayoutReport | null);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const legHits = useMemo(() => {
    const maybe = (report?.details as { legHits?: unknown } | undefined)?.legHits;
    return Array.isArray(maybe) ? (maybe as boolean[]) : [];
  }, [report?.details]);

  const hitCount = useMemo(() => legHits.filter(Boolean).length, [legHits]);

  const bottom = (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      <button
        type="button"
        onClick={() => router.push(`/tickets/${encodeURIComponent(id)}/edit`)}
        style={{
          width: "100%",
          border: "1px solid #111",
          background: "#fff",
          color: "#111",
          padding: "12px 14px",
          borderRadius: 14,
          fontSize: 16,
          fontWeight: 650,
        }}
      >
        返回校对
      </button>
      <button
        type="button"
        onClick={() => {
          // 前端占位：先落到本地记账本；后端接入后替换为 API 落账
          const now = new Date();
          const y = now.getFullYear();
          const m = String(now.getMonth() + 1).padStart(2, "0");
          const d = String(now.getDate()).padStart(2, "0");
          const date = `${y}-${m}-${d}`;

          const stake = 0;
          const payout = Number(report?.totalPayout ?? 0);
          const status = report?.status === "pending" ? "pending" : "settled";
          addTicket({ id, date, stake, payout, status });
          router.push(`/wanzhan/ledger/day/${encodeURIComponent(date)}`);
        }}
        style={{
          width: "100%",
          border: "1px solid #111",
          background: "#111",
          color: "#fff",
          padding: "12px 14px",
          borderRadius: 14,
          fontSize: 16,
          fontWeight: 650,
        }}
      >
        记入账本
      </button>
    </div>
  );

  return (
    <WanzhanShell title="计算报告" back bottom={bottom}>
      {loading ? <div style={{ color: "#666", fontSize: 14 }}>加载中...</div> : null}

      {error ? (
        <div
          style={{
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

      {!loading && !error && !report ? (
        <div style={cardStyle()}>
          <div style={{ fontWeight: 650, marginBottom: 6 }}>暂无报告</div>
          <div style={{ color: "#666", fontSize: 13 }}>
            还没有计算结果，或服务端未返回 report。
          </div>
        </div>
      ) : null}

      {report ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={cardStyle()}>
            {(() => {
              const meta = statusMeta(report.status);
              return (
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    border: `1px solid ${meta.border}`,
                    background: meta.bg,
                    color: meta.color,
                    borderRadius: 999,
                    padding: "6px 10px",
                    fontSize: 13,
                    fontWeight: 650,
                  }}
                >
                  {meta.label}
                </div>
              );
            })()}

            <div
              style={{
                marginTop: 10,
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
              }}
            >
              <div>
                <div style={{ fontSize: 12, color: "#666", marginBottom: 6 }}>预计总奖金</div>
                <div style={{ fontSize: 22, fontWeight: 750 }}>{formatMoney(report.totalPayout)}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: "#666", marginBottom: 6 }}>命中情况</div>
                <div style={{ fontSize: 14, fontWeight: 650 }}>
                  {hitCount}/{legHits.length || ticket?.legs.length || 0} 命中
                </div>
              </div>
            </div>
          </div>

          <div style={cardStyle()}>
            <div style={{ fontWeight: 650, marginBottom: 10 }}>Leg 命中明细</div>
            {ticket?.legs?.length ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {ticket.legs.map((leg, i) => {
                  const hit = legHits[i];
                  const ok = hit === true;
                  const known = typeof hit === "boolean";
                  return (
                    <div
                      key={`${leg.matchKey}-${i}`}
                      style={{
                        border: "1px solid #eee",
                        borderRadius: 12,
                        padding: 10,
                        background: "#fff",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                        <div style={{ fontWeight: 650, fontSize: 14 }}>第 {i + 1} 场</div>
                        <div
                          style={{
                            fontSize: 12,
                            fontWeight: 650,
                            color: known ? (ok ? "#135200" : "#b42318") : "#666",
                          }}
                        >
                          {known ? (ok ? "命中" : "未命中") : "未知"}
                        </div>
                      </div>
                      <div style={{ marginTop: 6, fontSize: 13, color: "#111" }}>{leg.matchKey}</div>
                      <div style={{ marginTop: 6, fontSize: 12, color: "#666" }}>
                        选择：{leg.selection}，SP：{leg.sp}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ color: "#666", fontSize: 13 }}>无 legs 信息。</div>
            )}
          </div>

          <div style={cardStyle()}>
            <div style={{ fontWeight: 650, marginBottom: 10 }}>无法匹配赛果</div>
            {report.unmatchedLegs?.length ? (
              <ul style={{ margin: 0, paddingLeft: 18, color: "#7a4f01", fontSize: 13 }}>
                {report.unmatchedLegs.map((k) => (
                  <li key={k}>{k}</li>
                ))}
              </ul>
            ) : (
              <div style={{ color: "#666", fontSize: 13 }}>全部 legs 已匹配。</div>
            )}
          </div>
        </div>
      ) : null}
    </WanzhanShell>
  );
}
