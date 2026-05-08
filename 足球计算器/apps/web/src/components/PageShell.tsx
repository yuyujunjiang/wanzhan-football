"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";

export function PageShell(props: {
  title: string;
  children: ReactNode;
  bottom?: ReactNode;
  back?: boolean;
}) {
  const router = useRouter();

  return (
    <div
      style={{
        minHeight: "100dvh",
        fontFamily: "system-ui, -apple-system, sans-serif",
        background: "#f6f7f9",
        color: "#111",
      }}
    >
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "#fff",
          borderBottom: "1px solid #eee",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "12px 12px",
            maxWidth: 720,
            margin: "0 auto",
          }}
        >
          {props.back ? (
            <button
              type="button"
              onClick={() => router.back()}
              style={{
                border: "1px solid #ddd",
                background: "#fff",
                padding: "8px 10px",
                borderRadius: 10,
                fontSize: 14,
              }}
            >
              返回
            </button>
          ) : null}
          <div style={{ fontWeight: 650, fontSize: 16 }}>{props.title}</div>
        </div>
      </header>

      <main
        style={{
          maxWidth: 720,
          margin: "0 auto",
          padding: "12px 12px 96px",
        }}
      >
        {props.children}
      </main>

      {props.bottom ? (
        <div
          style={{
            position: "fixed",
            bottom: 0,
            left: 0,
            right: 0,
            background: "rgba(246, 247, 249, 0.9)",
            backdropFilter: "blur(10px)",
            borderTop: "1px solid #eee",
          }}
        >
          <div style={{ maxWidth: 720, margin: "0 auto", padding: 12 }}>
            {props.bottom}
          </div>
        </div>
      ) : null}
    </div>
  );
}

