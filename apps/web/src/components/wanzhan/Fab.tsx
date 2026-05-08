"use client";

export function Fab(props: { href: string; label: string }) {
  return (
    <a
      href={props.href}
      style={{
        position: "fixed",
        right: 16,
        bottom: 86,
        zIndex: 20,
        width: 56,
        height: 56,
        borderRadius: 999,
        background: "#111",
        color: "#fff",
        display: "grid",
        placeItems: "center",
        textDecoration: "none",
        fontSize: 26,
        fontWeight: 800,
        boxShadow: "0 10px 30px rgba(0,0,0,0.18)",
        border: "1px solid rgba(255,255,255,0.12)",
      }}
      aria-label={props.label}
      title={props.label}
    >
      +
    </a>
  );
}

