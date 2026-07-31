"use client";

import { useEffect, useRef } from "react";

import BrandLogo from "./BrandLogo";
import ChatBubble from "./ChatBubble";
import type { ChatAction, ChatContext, ChatSuggestion } from "@/lib/types";


export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  message: string;
  action?: ChatAction;
  suggestions?: ChatSuggestion[];
};

type ChatWindowProps = {
  messages: ChatMessage[];
  isLoading: boolean;
  pendingActionId: string | null;
  context: ChatContext | null;
  onAction: (messageId: string, action: ChatAction, confirm: boolean) => void;
  onSuggestion: (value: string) => void;
};

function contextLabel(context: ChatContext): string | null {
  if (context.status === "collecting_fields") {
    const waiting = context.awaiting_field?.replaceAll("_", " ");
    return waiting ? `Waiting for ${waiting}` : "Collecting information";
  }
  if (context.status === "awaiting_clarification") {
    return `Choosing between ${context.candidate_count} matches`;
  }
  if (context.status === "awaiting_confirmation") {
    return "Deletion awaiting confirmation";
  }
  if (context.selected_user) {
    const name = context.selected_user.name || context.selected_user.email;
    return `Current user: ${String(name)}`;
  }
  return null;
}

function ThinkingIndicator() {
  return (
    <div className="flex items-start gap-3" aria-live="polite" aria-label="Assistant is thinking">
      <div className="mt-1 shrink-0" aria-hidden="true">
        <BrandLogo size="sm" />
      </div>
      <div className="rounded-2xl rounded-tl-md border border-white/10 bg-white/5 px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-300">Thinking</span>
          <span className="flex items-center gap-1" aria-hidden="true">
            {[0, 1, 2].map((item) => (
              <span
                key={item}
                className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-300"
                style={{ animationDelay: `${item * 180}ms`, animationDuration: "900ms" }}
              />
            ))}
          </span>
        </div>
        <p className="mt-1 text-[11px] text-slate-500">Understanding your request and checking the current context…</p>
      </div>
    </div>
  );
}

export default function ChatWindow({
  messages,
  isLoading,
  pendingActionId,
  context,
  onAction,
  onSuggestion,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const label = context ? contextLabel(context) : null;

  return (
    <main className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto flex max-w-4xl flex-col gap-5">
        <div className="rounded-2xl border border-indigo-400/20 bg-gradient-to-r from-indigo-400/10 to-violet-400/5 p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-medium leading-6 text-indigo-100">
              Speak naturally. I can remember the current user, collect missing
              information, clarify duplicate names, and safely manage records.
            </p>
            {context && (
              <span className="rounded-full border border-white/10 bg-slate-950/50 px-3 py-1 text-[11px] font-medium text-slate-300">
                {context.ai_mode === "openai" ? "AI understanding" : "Safe fallback"}
              </span>
            )}
          </div>
          {label && (
            <div className="mt-3 rounded-xl border border-white/10 bg-slate-950/40 px-3 py-2 text-xs text-slate-300">
              {label}
            </div>
          )}
        </div>

        {messages.map((chatMessage) => (
          <ChatBubble
            key={chatMessage.id}
            role={chatMessage.role}
            message={chatMessage.message}
            action={chatMessage.action}
            suggestions={chatMessage.suggestions}
            actionPending={isLoading || pendingActionId === chatMessage.id}
            onAction={
              chatMessage.action
                ? (action, confirm) => onAction(chatMessage.id, action, confirm)
                : undefined
            }
            onSuggestion={onSuggestion}
          />
        ))}

        {isLoading && <ThinkingIndicator />}

        <div ref={bottomRef} />
      </div>
    </main>
  );
}