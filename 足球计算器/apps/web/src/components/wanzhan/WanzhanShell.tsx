"use client";

import type { ReactNode } from "react";
import { PageShell } from "../PageShell";
import { TabBar } from "./TabBar";

export function WanzhanShell(props: {
  title: string;
  children: ReactNode;
  top?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <>
      <PageShell title={props.title} back={false} bottom={<TabBar />} right={props.right}>
        {props.top ? <div style={{ marginBottom: 12 }}>{props.top}</div> : null}
        {props.children}
      </PageShell>
    </>
  );
}

