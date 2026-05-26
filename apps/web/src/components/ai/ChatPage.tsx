"use client";

import { FormEvent, useRef, useState } from "react";

import {
  ChatMessagePayload,
  streamAiChat
} from "../../lib/aiChatStream";
import {
  buildTodayRecommendApiContent,
  fetchMatchDayCache,
  TODAY_RECOMMEND_LABEL
} from "../../lib/matchDayCache";

import { ChatMarkdown } from "./ChatMarkdown";
import styles from "./ChatPage.module.css";

type MessageStatus = "streaming" | "done" | "error" | "stopped";

type Message = {
  role: "user" | "assistant";
  content: string;
  apiContent?: string;
  status: MessageStatus;
};

const PROMPTS = [
  TODAY_RECOMMEND_LABEL,
  "帮我复盘这张票哪里判断错了",
  "解释一下让球胜平负怎么理解"
];

const THINKING_TEXT = "正在思考...";
const STOPPED_TEXT = "已停止";

function toChatPayload(messages: Message[]): ChatMessagePayload[] {
  return messages
    .filter((message) => message.role === "user" || message.status === "done")
    .map((message) => ({
      role: message.role,
      content: message.apiContent ?? message.content
    }));
}

function isConfigError(message: string): boolean {
  return message.includes("未配置");
}

function shouldRenderMarkdown(message: Message): boolean {
  if (message.role !== "assistant") return false;
  if (message.status === "error") return false;
  if (message.content === THINKING_TEXT || message.content === STOPPED_TEXT) {
    return false;
  }
  return true;
}

function renderMessageBody(message: Message) {
  if (shouldRenderMarkdown(message)) {
    return <ChatMarkdown content={message.content} />;
  }
  return message.content;
}

export function ChatPage({ embedded = false }: { embedded?: boolean }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [connectionLabel, setConnectionLabel] = useState("待连接");
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeAssistantIndexRef = useRef<number | null>(null);
  const streamingRef = useRef(false);

  const updateAssistantAt = (
    assistantIndex: number,
    updater: (message: Message) => Message
  ) => {
    setMessages((currentMessages) =>
      currentMessages.map((message, index) =>
        index === assistantIndex ? updater(message) : message
      )
    );
  };

  const updateActiveAssistant = (updater: (message: Message) => Message) => {
    const activeIndex = activeAssistantIndexRef.current;
    if (activeIndex === null) return;

    updateAssistantAt(activeIndex, updater);
  };

  const sendText = async (
    text: string,
    baseMessages = messages,
    options?: { apiContent?: string }
  ) => {
    const trimmedText = text.trim();
    if (!trimmedText || streamingRef.current) return;

    streamingRef.current = true;

    const userMessage: Message = {
      role: "user",
      content: trimmedText,
      apiContent: options?.apiContent,
      status: "done"
    };
    const assistantMessage: Message = {
      role: "assistant",
      content: THINKING_TEXT,
      status: "streaming"
    };
    const nextMessages = [...baseMessages, userMessage, assistantMessage];
    const assistantIndex = nextMessages.length - 1;
    const controller = new AbortController();
    let sawDone = false;
    let sawError = false;

    setMessages(nextMessages);
    setInputValue("");
    setIsStreaming(true);
    setConnectionLabel("连接中");
    abortControllerRef.current = controller;
    activeAssistantIndexRef.current = assistantIndex;

    try {
      await streamAiChat({
        messages: toChatPayload([...baseMessages, userMessage]),
        signal: controller.signal,
        onChunk: (content) => {
          if (controller.signal.aborted) return;
          setConnectionLabel("生成中");
          updateAssistantAt(assistantIndex, (message) => {
            if (message.status === "stopped") return message;
            return {
              ...message,
              content:
                message.content === THINKING_TEXT
                  ? content
                  : message.content + content
            };
          });
        },
        onDone: () => {
          if (controller.signal.aborted) return;
          sawDone = true;
          setConnectionLabel("可用");
          updateAssistantAt(assistantIndex, (message) => {
            if (message.status === "stopped") return message;
            return {
              ...message,
              content:
                message.content === THINKING_TEXT ? "暂无回答" : message.content,
              status: "done"
            };
          });
        },
        onError: (message) => {
          if (controller.signal.aborted) return;
          sawError = true;
          setConnectionLabel(isConfigError(message) ? "未配置" : "不可用");
          updateAssistantAt(assistantIndex, (currentMessage) => {
            if (currentMessage.status === "stopped") return currentMessage;
            return {
              ...currentMessage,
              content: message,
              status: "error"
            };
          });
        }
      });

      if (!sawDone && !sawError && !controller.signal.aborted) {
        setConnectionLabel("可用");
        updateAssistantAt(assistantIndex, (message) => {
          if (message.status === "stopped") return message;
          return {
            ...message,
            content: message.content === THINKING_TEXT ? "暂无回答" : message.content,
            status: "done"
          };
        });
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
        activeAssistantIndexRef.current = null;
        setIsStreaming(false);
        streamingRef.current = false;
      }
    }
  };

  const stopStreaming = () => {
    if (!isStreaming) return;

    abortControllerRef.current?.abort();
    setConnectionLabel("已停止");
    streamingRef.current = false;
    updateActiveAssistant((message) => ({
      ...message,
      content: message.content === THINKING_TEXT ? STOPPED_TEXT : message.content,
      status: "stopped"
    }));
    setIsStreaming(false);
  };

  const sendTodayRecommend = async (baseMessages = messages) => {
    if (streamingRef.current) return;

    try {
      const cache = await fetchMatchDayCache();
      void sendText(TODAY_RECOMMEND_LABEL, baseMessages, {
        apiContent: buildTodayRecommendApiContent(cache)
      });
    } catch {
      void sendText(TODAY_RECOMMEND_LABEL, baseMessages, {
        apiContent: TODAY_RECOMMEND_LABEL
      });
    }
  };

  const retryMessageAt = async (assistantIndex: number) => {
    const userIndex = messages
      .slice(0, assistantIndex)
      .findLastIndex((message) => message.role === "user");
    if (userIndex === -1) return;

    const userMessage = messages[userIndex];
    if (userMessage.content === TODAY_RECOMMEND_LABEL) {
      await sendTodayRecommend(messages.slice(0, userIndex));
      return;
    }

    void sendText(userMessage.content, messages.slice(0, userIndex), {
      apiContent: userMessage.apiContent
    });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendText(inputValue);
  };

  return (
    <main className={embedded ? `${styles.page} ${styles.embedded}` : styles.page}>
      {embedded ? (
        <div className={styles.embeddedStatus} aria-live="polite">
          {connectionLabel}
        </div>
      ) : (
        <header className={styles.header}>
          <h1>AI数据</h1>
          <span className={styles.status}>{connectionLabel}</span>
        </header>
      )}

      <section className={styles.messages} aria-live="polite">
        {messages.length === 0 ? (
          <div className={styles.welcome}>
            <p className={styles.welcomeTitle}>问我比赛数据、盘口理解或赛后复盘。</p>
            <div className={styles.prompts}>
              {PROMPTS.map((prompt, index) => (
                <button
                  className={`${styles.prompt} ${
                    index === 0 ? styles.primaryPrompt : ""
                  }`}
                  disabled={isStreaming}
                  key={prompt}
                  onClick={() =>
                    void (prompt === TODAY_RECOMMEND_LABEL
                      ? sendTodayRecommend()
                      : sendText(prompt))
                  }
                  type="button"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <article
              className={`${styles.bubble} ${
                message.role === "user"
                  ? styles.userBubble
                  : styles.assistantBubble
              }`}
              key={`${message.role}-${index}`}
            >
              {renderMessageBody(message)}
              {message.status === "error" ? (
                <button
                  className={styles.retryButton}
                  disabled={isStreaming}
                  onClick={() => retryMessageAt(index)}
                  type="button"
                >
                  重试
                </button>
              ) : null}
              {message.status === "stopped" && message.content !== STOPPED_TEXT ? (
                <span className={styles.stoppedMarker}>{STOPPED_TEXT}</span>
              ) : null}
            </article>
          ))
        )}
      </section>

      <form className={styles.composer} onSubmit={handleSubmit}>
        <input
          aria-label="输入问题"
          disabled={isStreaming}
          onChange={(event) => setInputValue(event.target.value)}
          placeholder="输入你的问题"
          value={inputValue}
        />
        {isStreaming ? (
          <button
            className={styles.stopButton}
            onClick={stopStreaming}
            type="button"
          >
            停止
          </button>
        ) : (
          <button
            disabled={!inputValue.trim()}
            className={styles.sendButton}
            type="submit"
          >
            发送
          </button>
        )}
      </form>
    </main>
  );
}
