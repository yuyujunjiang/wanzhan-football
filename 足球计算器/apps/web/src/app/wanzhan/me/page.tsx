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

function item(label: string, desc: string) {
  return (
    <div
      style={{
        border: "1px solid #eee",
        borderRadius: 12,
        padding: 10,
        background: "#fff",
      }}
    >
      <div style={{ fontWeight: 800 }}>{label}</div>
      <div style={{ marginTop: 6, fontSize: 12, color: "#666", lineHeight: 1.4 }}>{desc}</div>
    </div>
  );
}

export default function WanzhanMePage() {
  return (
    <WanzhanShell title="我的">
      <div style={cardStyle()}>
        <div style={{ fontWeight: 900, marginBottom: 10 }}>设置与管理（占位）</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {item("关注管理", "管理关注的联赛/球队/比赛")}
          {item("数据源/同步", "赛程/赛果数据源设置（后端接入后启用）")}
          {item("导入导出", "账单导出/备份")}
          {item("隐私与备份", "本地数据、匿名模式、清空缓存")}
        </div>
      </div>
    </WanzhanShell>
  );
}

