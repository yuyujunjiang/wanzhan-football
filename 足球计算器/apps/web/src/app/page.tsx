export default function HomePage() {
  return (
    <main style={{ padding: 16, fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h1 style={{ margin: 0, fontSize: 24 }}>Football Calculator</h1>
      <p style={{ marginTop: 8, color: "#555" }}>MVP scaffold</p>
      <a
        href="/upload"
        style={{
          display: "inline-block",
          marginTop: 12,
          padding: "10px 12px",
          borderRadius: 12,
          background: "#111",
          color: "#fff",
          textDecoration: "none",
          fontWeight: 650,
        }}
      >
        去上传识别
      </a>
    </main>
  );
}

