"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { PageShell } from "../../../../components/PageShell";
import { TicketEditor } from "../../../../components/TicketEditor";
import { calculateTicket, getTicket, validateTicket, type Ticket } from "../../../../lib/api";

const defaultTicket: Ticket = {
  ticketType: "jc-football",
  playType: "SPF",
  multiplier: 1,
  passTypes: ["2x1"],
  legs: [],
};

export default function TicketEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [loading, setLoading] = useState(true);
  const [ticket, setTicket] = useState<Ticket>(defaultTicket);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<{ ok: boolean; errors?: string[] } | null>(
    null,
  );
  const [actionLoading, setActionLoading] = useState<"validate" | "calculate" | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setValidation(null);
      try {
        const res = await getTicket(id);
        if (cancelled) return;
        setTicket(res.ticket ?? defaultTicket);
        setWarnings([]);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const canValidate = useMemo(() => !loading && !actionLoading, [loading, actionLoading]);
  const canCalculate = useMemo(
    () => !loading && !actionLoading && ticket.legs.length > 0,
    [loading, actionLoading, ticket.legs.length],
  );

  const bottom = (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      <button
        type="button"
        disabled={!canValidate}
        onClick={async () => {
          setActionLoading("validate");
          setValidation(null);
          setError(null);
          try {
            const res = await validateTicket(ticket);
            if ("errors" in res) setValidation({ ok: false, errors: res.errors });
            else setValidation({ ok: true });
          } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
          } finally {
            setActionLoading(null);
          }
        }}
        style={{
          border: "1px solid #111",
          background: "#fff",
          color: "#111",
          padding: "12px 12px",
          borderRadius: 14,
          fontSize: 15,
          fontWeight: 650,
        }}
      >
        {actionLoading === "validate" ? "检查中..." : "校验/检查"}
      </button>

      <button
        type="button"
        disabled={!canCalculate}
        onClick={async () => {
          setActionLoading("calculate");
          setError(null);
          try {
            const res = await calculateTicket(ticket);
            if ("ok" in res && res.ok === false) {
              setValidation({ ok: false, errors: res.errors });
              return;
            }
            if (!("id" in res)) throw new Error("calculate response missing id");
            router.push(`/tickets/${encodeURIComponent(res.id)}/report`);
          } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
          } finally {
            setActionLoading(null);
          }
        }}
        style={{
          border: "1px solid #111",
          background: canCalculate ? "#111" : "#999",
          color: "#fff",
          padding: "12px 12px",
          borderRadius: 14,
          fontSize: 15,
          fontWeight: 650,
        }}
      >
        {actionLoading === "calculate" ? "计算中..." : "计算奖金"}
      </button>
    </div>
  );

  return (
    <PageShell title="校对票据" back bottom={bottom}>
      {loading ? (
        <div style={{ color: "#666", fontSize: 14 }}>加载中...</div>
      ) : null}

      {error ? (
        <div
          style={{
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

      {warnings.length ? (
        <div
          style={{
            background: "#fff",
            border: "1px solid #ffe58f",
            color: "#7a4f01",
            borderRadius: 14,
            padding: 12,
            fontSize: 13,
          }}
        >
          <div style={{ fontWeight: 650, marginBottom: 6 }}>提示</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {validation ? (
        <div
          style={{
            marginTop: 12,
            background: "#fff",
            border: `1px solid ${validation.ok ? "#b7eb8f" : "#f1c0c0"}`,
            color: validation.ok ? "#135200" : "#b42318",
            borderRadius: 14,
            padding: 12,
            fontSize: 13,
          }}
        >
          {validation.ok ? (
            "校验通过"
          ) : (
            <>
              <div style={{ fontWeight: 650, marginBottom: 6 }}>校验失败</div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {(validation.errors ?? []).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      ) : null}

      <div style={{ marginTop: 12 }}>
        <TicketEditor ticket={ticket} onChange={setTicket} />
      </div>
    </PageShell>
  );
}

