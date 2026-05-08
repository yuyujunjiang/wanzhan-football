"use client";

import { useEffect, useMemo, useState } from "react";
import { PageShell } from "../../components/PageShell";
import { API_BASE_URL } from "../../lib/api";

type MatchItem = {
  date: string;
  league: string;
  homeTeam: string;
  awayTeam: string;
  kickoffTime: string;
  matchKey: string;
  matchStatus?: string;
  finalScore?: string | null;
  outcomeSPF?: string;
  outcomeRQSPF?: string;
};

function formatLocalDateYYYYMMDD(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function cardStyle() {
  return {
    background: "#fff",
    border: "1px solid #eee",
    borderRadius: 14,
    padding: 12,
  } as const;
}

export default function MatchesPage() {
  const [date, setDate] = useState(() => formatLocalDateYYYYMMDD(new Date()));

  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<MatchItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load(d: string) {
    let cancelled = false;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/matches?date=${encodeURIComponent(d)}`);
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`API ${res.status} /api/matches${text ? `: ${text}` : ""}`);
      }
      const body = (await res.json()) as unknown;
      if (!Array.isArray(body)) throw new Error("matches response is not a list");
      if (cancelled) return;
      setItems(body as MatchItem[]);
    } catch (e) {
      if (cancelled) return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (!cancelled) setLoading(false);
    }
    return () => {
      cancelled = true;
    };
  }

  useEffect(() => {
    void load(date);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <PageShell title="赛程/赛果" back>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ color: "#666", fontSize: 13 }}>日期</div>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.currentTarget.value)}
            style={{
              border: "1px solid #ddd",
              borderRadius: 10,
              padding: "8px 10px",
              fontSize: 14,
            }}
          />
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            type="button"
            onClick={() => void load(date)}
            style={{
              border: "1px solid #ddd",
              background: "#fff",
              padding: "8px 10px",
              borderRadius: 10,
              fontSize: 14,
            }}
          >
            刷新
          </button>
          <a
            href="/upload"
            style={{
              border: "1px solid #ddd",
              background: "#fff",
              padding: "8px 10px",
              borderRadius: 10,
              fontSize: 14,
              textDecoration: "none",
              color: "#111",
              whiteSpace: "nowrap",
            }}
          >
            去上传
          </a>
        </div>
      </div>

      {loading ? <div style={{ marginTop: 12, color: "#666", fontSize: 14 }}>加载中...</div> : null}

      {error ? (
        <div
          style={{
            marginTop: 12,
            background: "#fff",
            border: "1px solid #f1c0c0",
            color: "#b42318",
            borderRadius: 14,
            padding: 12,
            fontSize: 13,
            whiteSpace: "pre-wrap",
          }}
        >
          {error}
        </div>
      ) : null}

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((m) => (
          <div key={m.matchKey} style={cardStyle()}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
              <div style={{ fontWeight: 650 }}>{m.league}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {m.finalScore ? (
                  <div style={{ fontSize: 13, fontWeight: 750 }}>{m.finalScore}</div>
                ) : (
                  <div style={{ fontSize: 13, color: "#666" }}>
                    {new Date(m.kickoffTime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                )}
                {m.matchStatus ? (
                  <div
                    style={{
                      fontSize: 12,
                      padding: "2px 8px",
                      borderRadius: 999,
                      border: "1px solid #eee",
                      color: "#555",
                      background: "#fafafa",
                    }}
                  >
                    {m.matchStatus}
                  </div>
                ) : null}
              </div>
            </div>

            <div style={{ marginTop: 8, fontSize: 16, fontWeight: 700 }}>
              {m.homeTeam} <span style={{ color: "#999" }}>vs</span> {m.awayTeam}
            </div>

            <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div
                style={{
                  border: "1px solid #eee",
                  borderRadius: 12,
                  padding: 10,
                  background: "#fff",
                }}
              >
                <div style={{ fontSize: 12, color: "#666" }}>SPF</div>
                <div style={{ marginTop: 4, fontWeight: 650 }}>{m.outcomeSPF ?? "-"}</div>
              </div>
              <div
                style={{
                  border: "1px solid #eee",
                  borderRadius: 12,
                  padding: 10,
                  background: "#fff",
                }}
              >
                <div style={{ fontSize: 12, color: "#666" }}>RQSPF</div>
                <div style={{ marginTop: 4, fontWeight: 650 }}>{m.outcomeRQSPF ?? "-"}</div>
              </div>
            </div>

            <div style={{ marginTop: 8, fontSize: 12, color: "#666", wordBreak: "break-word" }}>
              matchKey：{m.matchKey}
            </div>
          </div>
        ))}

        {!loading && !error && items.length === 0 ? (
          <div style={cardStyle()}>
            <div style={{ fontWeight: 650, marginBottom: 6 }}>暂无比赛</div>
            <div style={{ color: "#666", fontSize: 13 }}>该日期没有返回任何比赛。</div>
          </div>
        ) : null}
      </div>
    </PageShell>
  );
}

