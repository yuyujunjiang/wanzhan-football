"use client";

import { ChatPage } from "../../../components/ai/ChatPage";
import { WanzhanShell } from "../../../components/wanzhan/WanzhanShell";

export default function WanzhanAiPage() {
  return (
    <WanzhanShell title="AI数据">
      <ChatPage embedded />
    </WanzhanShell>
  );
}
