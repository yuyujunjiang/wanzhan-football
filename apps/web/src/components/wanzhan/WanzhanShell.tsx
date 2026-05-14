"use client";

import type { ReactNode } from "react";
import { PageShell } from "../PageShell";
import { TabBar } from "./TabBar";

export function WanzhanShell(props: {
  title: string;
  children: ReactNode;
  top?: ReactNode;
  bottom?: ReactNode;
  back?: boolean;
  right?: ReactNode;
}) {
  return (
    <>
      <PageShell
        title={props.title}
        back={props.back ?? false}
        subHeader={<TabBar />}
        right={props.right}
        bottom={props.bottom}
      >
        {props.top ? <div style={{ marginBottom: 12 }}>{props.top}</div> : null}
        {props.children}
      </PageShell>
    </>
  );
}
