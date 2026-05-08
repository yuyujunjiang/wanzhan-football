"use client";

export function StatStrip(props: {
  profitToday: number | null;
  pendingCount: number | null;
  onOpenTodayTickets?: () => void;
  onOpenPendingTickets?: () => void;
}) {
  const profit = props.profitToday;
  const profitText = profit === null ? "-" : profit.toFixed(2);
  const profitColor = profit === null ? "#111" : profit >= 0 ? "#135200" : "#b42318";
  const profitBg = profit === null ? "#fff" : profit >= 0 ? "#f6ffed" : "#fff1f0";
  const profitBorder = profit === null ? "#eee" : profit >= 0 ? "#b7eb8f" : "#f1c0c0";

  const pendingText = props.pendingCount === null ? "-" : String(props.pendingCount);

  const box = (click?: (() => void) | undefined) =>
    ({
      flex: 1,
      border: "1px solid #eee",
      background: "#fff",
      borderRadius: 14,
      padding: 12,
      cursor: click ? "pointer" : "default",
    }) as const;

  return (
    <div style={{ display: "flex", gap: 10 }}>
      <div
        role={props.onOpenTodayTickets ? "button" : undefined}
        tabIndex={props.onOpenTodayTickets ? 0 : undefined}
        onClick={props.onOpenTodayTickets}
        style={{
          ...box(props.onOpenTodayTickets),
          border: `1px solid ${profitBorder}`,
          background: profitBg,
        }}
      >
        <div style={{ fontSize: 12, color: "#666" }}>今日盈亏</div>
        <div style={{ marginTop: 6, fontSize: 18, fontWeight: 800, color: profitColor }}>
          {profitText}
        </div>
      </div>
      <div
        role={props.onOpenPendingTickets ? "button" : undefined}
        tabIndex={props.onOpenPendingTickets ? 0 : undefined}
        onClick={props.onOpenPendingTickets}
        style={box(props.onOpenPendingTickets)}
      >
        <div style={{ fontSize: 12, color: "#666" }}>待结票</div>
        <div style={{ marginTop: 6, fontSize: 18, fontWeight: 800 }}>{pendingText}</div>
      </div>
    </div>
  );
}

