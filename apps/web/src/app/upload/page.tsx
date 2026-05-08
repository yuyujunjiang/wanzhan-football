"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ImageUpload } from "../../components/ImageUpload";
import { PageShell } from "../../components/PageShell";
import { recognizeTicket } from "../../lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => files.length > 0 && !loading, [files.length, loading]);

  return (
    <PageShell
      title="上传识别"
      back
      bottom={
        <button
          type="button"
          disabled={!canSubmit}
          onClick={async () => {
            setLoading(true);
            setError(null);
            try {
              const res = await recognizeTicket(files);
              router.push(`/tickets/${encodeURIComponent(res.id)}/edit`);
            } catch (e) {
              setError(e instanceof Error ? e.message : String(e));
            } finally {
              setLoading(false);
            }
          }}
          style={{
            width: "100%",
            border: "1px solid #111",
            background: canSubmit ? "#111" : "#999",
            color: "#fff",
            padding: "12px 14px",
            borderRadius: 14,
            fontSize: 16,
            fontWeight: 650,
          }}
        >
          {loading ? "识别中..." : "开始识别"}
        </button>
      }
    >
      <ImageUpload files={files} onFilesChange={setFiles} disabled={loading} />
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
    </PageShell>
  );
}

