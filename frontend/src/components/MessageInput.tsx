"use client";

import type { RefObject } from "react";
import { useState } from "react";


type MessageInputProps = {
  onSend: (message: string) => Promise<void>;
  disabled: boolean;
  inputRef: RefObject<HTMLTextAreaElement | null>;
};

export default function MessageInput({
  onSend,
  disabled,
  inputRef,
}: MessageInputProps) {
  const [message, setMessage] = useState("");

  const handleSend = async () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || disabled) {
      return;
    }

    setMessage("");
    await onSend(trimmedMessage);
  };

  return (
    <div className="border-t border-white/10 bg-slate-950/90 px-4 py-4 backdrop-blur sm:px-6 sm:py-5">
      <div className="mx-auto flex max-w-4xl items-end gap-3 rounded-2xl border border-white/10 bg-white/5 p-3 shadow-lg shadow-black/10 transition focus-within:border-indigo-400/40 focus-within:bg-white/[0.07]">
        <textarea
          ref={inputRef}
          rows={1}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void handleSend();
            }
          }}
          disabled={disabled}
          placeholder="Talk naturally — e.g. We have a new user called Sara..."
          aria-label="Chat command"
          className="max-h-40 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm text-white outline-none placeholder:text-slate-500 disabled:opacity-50"
        />

        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={disabled || !message.trim()}
          className="rounded-xl bg-indigo-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {disabled ? "Working..." : "Send"}
        </button>
      </div>

      <p className="mt-2 text-center text-[11px] text-slate-500">
        Enter sends · Shift + Enter adds a line · Press / to focus · Deletions require confirmation
      </p>
    </div>
  );
}