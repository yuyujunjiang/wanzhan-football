"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { WanzhanShell } from "../../../components/wanzhan/WanzhanShell";
import { getMe, logout, type AuthUser } from "../../../lib/api";

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
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const u = await getMe();
        if (!cancelled) setUser(u);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onLogout() {
    await logout();
    router.replace("/wanzhan/login");
  }

  return (
    <WanzhanShell title="我的">
      <div style={cardStyle()}>
        <div style={{ fontWeight: 900, marginBottom: 10 }}>账号</div>
        {error ? <div style={{ color: "#b42318", fontSize: 13, marginBottom: 8 }}>{error}</div> : null}
        {user ? (
          <div style={{ marginBottom: 12, fontSize: 14 }}>
            当前用户：<strong>{user.username}</strong>
          </div>
        ) : (
          <div style={{ marginBottom: 12, fontSize: 13, color: "#666" }}>加载中…</div>
        )}
        <button
          type="button"
          onClick={() => void onLogout()}
          style={{
            padding: "10px 14px",
            borderRadius: 12,
            border: "1px solid #111",
            background: "#fff",
            fontWeight: 700,
            fontSize: 14,
          }}
        >
          退出登录
        </button>
      </div>

      <div style={{ ...cardStyle(), marginTop: 12 }}>
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
