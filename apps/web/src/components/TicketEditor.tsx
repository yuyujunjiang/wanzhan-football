"use client";

import type { CSSProperties } from "react";
import type { Ticket, TicketLeg, TicketPlayType } from "../lib/api";

const cardStyle: CSSProperties = {
  background: "#fff",
  border: "1px solid #eee",
  borderRadius: 14,
  padding: 12,
};

function labelStyle(): CSSProperties {
  return { fontSize: 12, color: "#666", marginBottom: 6 };
}

function inputStyle(): CSSProperties {
  return {
    width: "100%",
    padding: "10px 10px",
    borderRadius: 10,
    border: "1px solid #ddd",
    fontSize: 14,
    background: "#fff",
  };
}

function selectionOptions(playType: TicketPlayType): string[] {
  return playType === "RQSPF" ? ["让胜", "让平", "让负"] : ["胜", "平", "负"];
}

function ensureSelection(playType: TicketPlayType, current: string): string {
  const opts = selectionOptions(playType);
  if (!current) return opts[0] ?? "";
  if (opts.includes(current)) return current;
  if (playType === "RQSPF") {
    if (current === "胜") return "让胜";
    if (current === "平") return "让平";
    if (current === "负") return "让负";
  }
  if (current === "让胜") return "胜";
  if (current === "让平") return "平";
  if (current === "让负") return "负";
  return opts[0] ?? current;
}

export function TicketEditor(props: {
  ticket: Ticket;
  onChange: (ticket: Ticket) => void;
}) {
  const ticket = props.ticket;

  const update = (patch: Partial<Ticket>) => props.onChange({ ...ticket, ...patch });

  const updateLeg = (idx: number, patch: Partial<TicketLeg>) => {
    const legs = ticket.legs.slice();
    legs[idx] = { ...legs[idx], ...patch };
    update({ legs });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={cardStyle}>
        <div style={{ fontWeight: 650, marginBottom: 10 }}>票据信息</div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <div style={labelStyle()}>玩法</div>
            <select
              value={ticket.playType}
              onChange={(e) => {
                const playType = e.currentTarget.value as TicketPlayType;
                const nextLegs = ticket.legs.map((l) => ({
                  ...l,
                  playType,
                  selection: ensureSelection(playType, l.selection),
                  handicap: playType === "RQSPF" ? l.handicap ?? 0 : null,
                }));
                update({ playType, legs: nextLegs });
              }}
              style={inputStyle()}
            >
              <option value="SPF">胜平负 (SPF)</option>
              <option value="RQSPF">让球胜平负 (RQSPF)</option>
            </select>
          </div>

          <div>
            <div style={labelStyle()}>倍数</div>
            <input
              type="number"
              min={1}
              value={ticket.multiplier}
              onChange={(e) => update({ multiplier: Number(e.currentTarget.value || 1) })}
              style={inputStyle()}
            />
          </div>
        </div>

        <div style={{ marginTop: 10 }}>
          <div style={labelStyle()}>串关（用逗号分隔，例如：2x1,3x1）</div>
          <input
            value={ticket.passTypes.join(",")}
            onChange={(e) =>
              update({
                passTypes: e.currentTarget.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
              })
            }
            placeholder="2x1"
            style={inputStyle()}
          />
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <div style={{ fontWeight: 650 }}>比赛明细</div>
        <button
          type="button"
          onClick={() =>
            update({
              legs: ticket.legs.concat({
                matchKey: "",
                playType: ticket.playType,
                selection: ensureSelection(ticket.playType, ""),
                handicap: ticket.playType === "RQSPF" ? 0 : null,
                sp: 1.0,
              }),
            })
          }
          style={{
            border: "1px solid #ddd",
            background: "#fff",
            padding: "8px 10px",
            borderRadius: 10,
            fontSize: 14,
          }}
        >
          + 添加一场
        </button>
      </div>

      {ticket.legs.map((leg, idx) => {
        const legPlayType = leg.playType ?? ticket.playType;
        const opts = selectionOptions(legPlayType);
        const selectionValues = opts.includes(leg.selection) ? opts : [leg.selection, ...opts];

        return (
          <div key={idx} style={cardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
              <div style={{ fontWeight: 650 }}>第 {idx + 1} 场</div>
              <button
                type="button"
                onClick={() => update({ legs: ticket.legs.filter((_, i) => i !== idx) })}
                style={{
                  border: "1px solid #f1c0c0",
                  background: "#fff",
                  color: "#b42318",
                  padding: "8px 10px",
                  borderRadius: 10,
                  fontSize: 14,
                }}
              >
                删除
              </button>
            </div>

            <div style={{ marginTop: 10 }}>
              <div style={labelStyle()}>matchKey（用于匹配比赛）</div>
              <input
                value={leg.matchKey}
                onChange={(e) => updateLeg(idx, { matchKey: e.currentTarget.value })}
                placeholder="例如：2026-05-08 EPL A vs B"
                style={inputStyle()}
              />
            </div>

            <div style={{ marginTop: 10 }}>
              <div style={labelStyle()}>本场玩法</div>
              <select
                value={legPlayType}
                onChange={(e) => {
                  const playType = e.currentTarget.value as TicketPlayType;
                  updateLeg(idx, {
                    playType,
                    selection: ensureSelection(playType, leg.selection),
                    handicap: playType === "RQSPF" ? leg.handicap ?? 0 : null,
                  });
                }}
                style={inputStyle()}
              >
                <option value="SPF">胜平负 (SPF)</option>
                <option value="RQSPF">让球胜平负 (RQSPF)</option>
              </select>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
              <div>
                <div style={labelStyle()}>选项</div>
                <select
                  value={leg.selection}
                  onChange={(e) => updateLeg(idx, { selection: e.currentTarget.value })}
                  style={inputStyle()}
                >
                  {selectionValues.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div style={labelStyle()}>SP（票面赔率）</div>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.01"
                  value={Number.isFinite(leg.sp) ? leg.sp : 0}
                  onChange={(e) => updateLeg(idx, { sp: Number(e.currentTarget.value || 0) })}
                  style={inputStyle()}
                />
              </div>
            </div>

            <div style={{ marginTop: 10, opacity: legPlayType === "RQSPF" ? 1 : 0.65 }}>
              <div style={labelStyle()}>让球（RQSPF 必填）</div>
              <input
                type="number"
                inputMode="decimal"
                step="1"
                value={leg.handicap ?? ""}
                onChange={(e) =>
                  updateLeg(idx, {
                    handicap:
                      e.currentTarget.value === ""
                        ? null
                        : Number(e.currentTarget.value),
                  })
                }
                placeholder={legPlayType === "RQSPF" ? "例如：+1" : "SPF 可留空"}
                style={inputStyle()}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
