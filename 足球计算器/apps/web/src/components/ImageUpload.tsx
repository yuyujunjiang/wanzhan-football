"use client";

import { useId } from "react";

export function ImageUpload(props: {
  files: File[];
  onFilesChange: (files: File[]) => void;
  disabled?: boolean;
}) {
  const inputId = useId();

  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #eee",
        borderRadius: 14,
        padding: 12,
      }}
    >
      <div style={{ fontWeight: 650, marginBottom: 8 }}>上传票面图片</div>
      <label
        htmlFor={inputId}
        style={{
          display: "block",
          border: "1px dashed #bbb",
          borderRadius: 12,
          padding: 14,
          textAlign: "center",
          background: "#fafafa",
          cursor: props.disabled ? "not-allowed" : "pointer",
          opacity: props.disabled ? 0.6 : 1,
        }}
      >
        选择图片（可多张）
      </label>
      <input
        id={inputId}
        type="file"
        accept="image/*"
        multiple
        disabled={props.disabled}
        style={{ display: "none" }}
        onChange={(e) => {
          const list = Array.from(e.currentTarget.files ?? []);
          props.onFilesChange(list);
        }}
      />

      {props.files.length ? (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: "#555", marginBottom: 6 }}>
            已选择 {props.files.length} 张：
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, color: "#333" }}>
            {props.files.map((f) => (
              <li key={`${f.name}-${f.size}-${f.lastModified}`} style={{ fontSize: 13 }}>
                {f.name}
              </li>
            ))}
          </ul>
          <button
            type="button"
            disabled={props.disabled}
            onClick={() => props.onFilesChange([])}
            style={{
              marginTop: 10,
              border: "1px solid #ddd",
              background: "#fff",
              padding: "8px 10px",
              borderRadius: 10,
              fontSize: 14,
            }}
          >
            清空
          </button>
        </div>
      ) : (
        <div style={{ marginTop: 10, fontSize: 12, color: "#666" }}>
          提示：尽量裁剪到票面区域，避免反光与模糊。
        </div>
      )}
    </div>
  );
}

