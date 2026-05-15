"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { WanzhanShell } from "../../../../../../components/wanzhan/WanzhanShell";
import {
  getLedgerTicket,
  type LedgerLegInput,
  type LedgerTicket,
  updateLedgerTicket,
} from "../../../../../../lib/api";

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 12,
    padding: 12,
  } as const;
}

function legToInput(leg: LedgerTicket["legs"][number]): LedgerLegInput {
  return {
    matchKey: leg.matchKey,
    matchId: leg.matchId ?? null,
    league: leg.league,
    homeTeam: leg.homeTeam,
    awayTeam: leg.awayTeam,
    kickoffTime: leg.kickoffTime ?? null,
    playType: leg.playType,
    selection: leg.selection,
    sp: leg.sp,
    handicap: leg.handicap ?? null,
  };
}

export default function WanzhanLedgerTicketEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [ticket, setTicket] = useState<LedgerTicket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [date, setDate] = useState("");
  const [multiplier, setMultiplier] = useState(1);
  const [legs, setLegs] = useState<LedgerLegInput[]>([]);
  const [stake, setStake] = useState(0);
  const [actualPayout, setActualPayout] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const t = await getLedgerTicket(id);
        if (cancelled) return;
        setTicket(t);
        setDate(t.date);
        setMultiplier(t.multiplier);
        setLegs(t.legs.map(legToInput));
        setStake(t.stake);
        setActualPayout(t.actualPayout);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  function updateLeg(i: number, patch: Partial<LedgerLegInput>) {
    setLegs((prev) => prev.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  }

  async function onSavePending() {
    if (!ticket) return;
    setSaving(true);
    setError(null);
    try {
      await updateLedgerTicket(ticket.id, { date, multiplier, legs });
      router.replace(`/wanzhan/ledger/tickets/${encodeURIComponent(ticket.id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function onSaveSettled() {
    if (!ticket) return;
    setSaving(true);
    setError(null);
    try {
      await updateLedgerTicket(ticket.id, { stake, actualPayout });
      router.replace(`/wanzhan/ledger/tickets/${encodeURIComponent(ticket.id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <WanzhanShell title="编辑票据" back>
      {loading ? <div style={{ ...cardStyle(), color: "#666" }}>加载中…</div> : null}
      {error ? <div style={{ ...cardStyle(), color: "#b42318", fontSize: 13 }}>{error}</div> : null}

      {ticket && ticket.status === "pending" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={cardStyle()}>
            <div style={{ fontWeight: 800, marginBottom: 8 }}>日期 / 倍数</div>
            <label style={{ fontSize: 12, color: "#666" }}>日期 YYYY-MM-DD</label>
            <input
              value={date}
              onChange={(e) => setDate(e.target.value)}
              style={{ width: "100%", padding: 8, marginTop: 4, marginBottom: 10, borderRadius: 8, border: "1px solid #ddd" }}
            />
            <label style={{ fontSize: 12, color: "#666" }}>倍数</label>
            <input
              type="number"
              min={1}
              value={multiplier}
              onChange={(e) => setMultiplier(Number(e.target.value) || 1)}
              style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 8, border: "1px solid #ddd" }}
            />
          </div>

          {legs.map((leg, i) => (
            <div key={i} style={cardStyle()}>
              <div style={{ fontWeight: 800, marginBottom: 8 }}>场次 {i + 1}</div>
              <Field label="matchKey" value={leg.matchKey} onChange={(v) => updateLeg(i, { matchKey: v })} />
              <Field label="联赛" value={leg.league} onChange={(v) => updateLeg(i, { league: v })} />
              <Field label="主队" value={leg.homeTeam} onChange={(v) => updateLeg(i, { homeTeam: v })} />
              <Field label="客队" value={leg.awayTeam} onChange={(v) => updateLeg(i, { awayTeam: v })} />
              <Field
                label="开赛 ISO"
                value={leg.kickoffTime ?? ""}
                onChange={(v) => updateLeg(i, { kickoffTime: v || null })}
              />
              <label style={{ fontSize: 12, color: "#666" }}>玩法</label>
              <select
                value={leg.playType}
                onChange={(e) => updateLeg(i, { playType: e.target.value as LedgerLegInput["playType"] })}
                style={{ width: "100%", padding: 8, marginTop: 4, marginBottom: 8, borderRadius: 8, border: "1px solid #ddd" }}
              >
                <option value="SPF">SPF</option>
                <option value="RQSPF">RQSPF</option>
              </select>
              <Field label="选项" value={leg.selection} onChange={(v) => updateLeg(i, { selection: v })} />
              <label style={{ fontSize: 12, color: "#666" }}>SP</label>
              <input
                type="number"
                step="0.01"
                value={leg.sp}
                onChange={(e) => updateLeg(i, { sp: Number(e.target.value) })}
                style={{ width: "100%", padding: 8, marginTop: 4, marginBottom: 8, borderRadius: 8, border: "1px solid #ddd" }}
              />
              <Field
                label="让球（可空）"
                value={leg.handicap === null || leg.handicap === undefined ? "" : String(leg.handicap)}
                onChange={(v) =>
                  updateLeg(i, {
                    handicap: v === "" ? null : Number(v),
                  })
                }
              />
            </div>
          ))}

          <button
            type="button"
            disabled={saving}
            onClick={() => void onSavePending()}
            style={{
              padding: 12,
              borderRadius: 12,
              border: "none",
              background: "#111",
              color: "#fff",
              fontWeight: 800,
            }}
          >
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      ) : null}

      {ticket && ticket.status === "settled" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={cardStyle()}>
            <div style={{ fontWeight: 800, marginBottom: 8 }}>已结票 · 仅可改投入与回报</div>
            <label style={{ fontSize: 12, color: "#666" }}>投入 stake</label>
            <input
              type="number"
              step="0.01"
              value={stake}
              onChange={(e) => setStake(Number(e.target.value))}
              style={{ width: "100%", padding: 8, marginTop: 4, marginBottom: 10, borderRadius: 8, border: "1px solid #ddd" }}
            />
            <label style={{ fontSize: 12, color: "#666" }}>实际回报 actualPayout</label>
            <input
              type="number"
              step="0.01"
              value={actualPayout}
              onChange={(e) => setActualPayout(Number(e.target.value))}
              style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 8, border: "1px solid #ddd" }}
            />
          </div>
          <button
            type="button"
            disabled={saving}
            onClick={() => void onSaveSettled()}
            style={{
              padding: 12,
              borderRadius: 12,
              border: "none",
              background: "#111",
              color: "#fff",
              fontWeight: 800,
            }}
          >
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      ) : null}
    </WanzhanShell>
  );
}

function Field(props: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <>
      <label style={{ fontSize: 12, color: "#666" }}>{props.label}</label>
      <input
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        style={{ width: "100%", padding: 8, marginTop: 4, marginBottom: 8, borderRadius: 8, border: "1px solid #ddd" }}
      />
    </>
  );
}
