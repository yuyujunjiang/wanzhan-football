"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { WanzhanShell } from "../../../../../components/wanzhan/WanzhanShell";
import { getLedgerTicket, type LedgerTicket } from "../../../../../lib/api";

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 8,
    padding: 12,
  } as const;
}

function money(value: number) {
  return value.toFixed(2);
}

function statusLabel(ticket: LedgerTicket) {
  if (ticket.status === "pending") return "待结";
  return ticket.profit > 0 ? "已中奖" : "未中奖";
}

function legStatusLabel(isHit?: boolean | null) {
  if (isHit === true) return "命中";
  if (isHit === false) return "未中";
  return "待定";
}

export default function WanzhanLedgerTicketPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [ticket, setTicket] = useState<LedgerTicket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setTicket(null);
      try {
        const next = await getLedgerTicket(id);
        if (!cancelled) setTicket(next);
      } catch (err) {
        if (!cancelled) {
          setTicket(null);
          setError(err instanceof Error ? err.message : "票据加载失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <WanzhanShell title="票据详情" back>
      {loading ? <div style={{ ...cardStyle(), color: "#666", fontSize: 13 }}>加载中...</div> : null}
      {error ? <div style={{ ...cardStyle(), color: "#b42318", fontSize: 13 }}>{error}</div> : null}

      {ticket ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={cardStyle()}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
              <div style={{ fontWeight: 900 }}>票 #{ticket.id.slice(0, 8)}</div>
              <div style={{ color: ticket.status === "pending" ? "#7a4f01" : "#135200", fontSize: 13, fontWeight: 800 }}>
                {statusLabel(ticket)}
              </div>
            </div>

            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <Info label="过关" value={ticket.passType} />
              <Info label="倍数" value={`${ticket.multiplier}`} />
              <Info label="投入" value={money(ticket.stake)} />
              <Info label="预计回报" value={money(ticket.estimatedPayout)} />
              {ticket.status === "settled" ? (
                <>
                  <Info label="实际回报" value={money(ticket.actualPayout)} />
                  <Info
                    label="盈亏"
                    value={money(ticket.profit)}
                    valueColor={ticket.profit >= 0 ? "#135200" : "#b42318"}
                  />
                </>
              ) : null}
            </div>
          </div>

          <div style={cardStyle()}>
            <div style={{ fontWeight: 900 }}>投注项</div>
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
              {ticket.legs.map((leg) => (
                <div key={leg.id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ color: "#666", fontSize: 12 }}>{leg.league}</div>
                      <div style={{ marginTop: 4, fontWeight: 800 }}>
                        {leg.homeTeam} vs {leg.awayTeam}
                      </div>
                    </div>
                    <div style={{ color: "#666", fontSize: 12, whiteSpace: "nowrap" }}>{legStatusLabel(leg.isHit)}</div>
                  </div>

                  <div style={{ marginTop: 8, color: "#666", fontSize: 12, lineHeight: 1.7 }}>
                    {leg.kickoffTime ? <div>开赛 {leg.kickoffTime}</div> : null}
                    <div>
                      {leg.playType} · 选 {leg.selection} · SP {leg.sp.toFixed(2)}
                      {leg.handicap !== null && leg.handicap !== undefined ? ` · 让球 ${leg.handicap}` : ""}
                    </div>
                    <div>赛果 {leg.resultSelection ?? "待定"}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </WanzhanShell>
  );
}

function Info(props: { label: string; value: string; valueColor?: string }) {
  return (
    <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 10 }}>
      <div style={{ color: "#666", fontSize: 12 }}>{props.label}</div>
      <div style={{ marginTop: 4, color: props.valueColor ?? "#111", fontWeight: 850 }}>{props.value}</div>
    </div>
  );
}
