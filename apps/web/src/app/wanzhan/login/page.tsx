"use client";

import { Suspense } from "react";
import { LoginForm } from "./LoginForm";

export default function WanzhanLoginPage() {
  return (
    <Suspense fallback={<div style={{ padding: 24, textAlign: "center" }}>加载中…</div>}>
      <LoginForm />
    </Suspense>
  );
}
