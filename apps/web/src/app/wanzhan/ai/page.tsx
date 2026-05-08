"use client";

import { WanzhanShell } from "../../../components/wanzhan/WanzhanShell";

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 12,
  } as const;
}

export default function WanzhanAiPage() {
  return (
    <WanzhanShell
      title="AI数据"
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
        <div style={{ fontWeight: 900, marginBottom: 6 }}>AI 辅助（占位）</div>
        <div style={{ fontSize: 13, color: "#666", lineHeight: 1.5 }}>
          这里后续展示：热度/偏离/置信度/趋势等。现在先保留页面结构与跳转入口，等后端/模型接入后填充数据。
        </div>
      </div>
    </WanzhanShell>
  );
}

