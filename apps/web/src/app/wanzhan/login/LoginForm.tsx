"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { login } from "../../../lib/api";

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 16,
    maxWidth: 400,
    margin: "0 auto",
  } as const;
}

export function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username.trim(), password);
      const next = search.get("next");
      router.replace(next && next.startsWith("/wanzhan") ? next : "/wanzhan/matches");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 16, minHeight: "100vh", background: "#f7f7f7" }}>
      <div style={{ paddingTop: 48 }}>
        <h1 style={{ textAlign: "center", fontSize: 20, marginBottom: 16 }}>万站 · 登录</h1>
        <form onSubmit={onSubmit} style={cardStyle()}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 6 }}>用户名</label>
          <input
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: 10,
              borderRadius: 10,
              border: "1px solid #ddd",
              marginBottom: 12,
            }}
          />
          <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 6 }}>密码</label>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: 10,
              borderRadius: 10,
              border: "1px solid #ddd",
              marginBottom: 12,
            }}
          />
          {error ? (
            <div style={{ color: "#b42318", fontSize: 13, marginBottom: 10 }}>{error}</div>
          ) : null}
          <button
            type="submit"
            disabled={loading || !username.trim() || !password}
            style={{
              width: "100%",
              padding: 12,
              borderRadius: 12,
              border: "none",
              background: "#111",
              color: "#fff",
              fontWeight: 800,
              fontSize: 15,
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "登录中…" : "登录"}
          </button>
        </form>
      </div>
    </div>
  );
}
