"use client";

import { usePathname } from "next/navigation";

const tabs = [
  { href: "/wanzhan/matches", label: "赛程赛果" },
  { href: "/wanzhan/ledger", label: "记账本" },
  { href: "/wanzhan/ai", label: "AI数据" },
  { href: "/wanzhan/me", label: "我的" },
] as const;

export function TabBar() {
  const pathname = usePathname() ?? "";

  return (
    <nav
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 8,
      }}
      aria-label="万战导航"
    >
      {tabs.map((t) => {
        const active = pathname === t.href || pathname.startsWith(`${t.href}/`);
        return (
          <a
            key={t.href}
            href={t.href}
            style={{
              textDecoration: "none",
              textAlign: "center",
              padding: "10px 8px",
              borderRadius: 12,
              border: `1px solid ${active ? "#cfe0ff" : "#eee"}`,
              background: active ? "#f0f5ff" : "#fff",
              color: active ? "#1d39c4" : "#111",
              fontSize: 12,
              fontWeight: active ? 700 : 600,
            }}
          >
            {t.label}
          </a>
        );
      })}
    </nav>
  );
}

