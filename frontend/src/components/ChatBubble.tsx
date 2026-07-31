import type { ChatAction, ChatSuggestion } from "@/lib/types";


type ChatBubbleProps = {
  role: "user" | "assistant";
  message: string;
  action?: ChatAction;
  suggestions?: ChatSuggestion[];
  actionPending?: boolean;
  onAction?: (action: ChatAction, confirm: boolean) => void;
  onSuggestion?: (value: string) => void;
};

export default function ChatBubble({
  role,
  message,
  action,
  suggestions = [],
  actionPending = false,
  onAction,
  onSuggestion,
}: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-2xl break-words rounded-2xl px-5 py-4 text-sm leading-7 shadow-sm ${
          isUser
            ? "rounded-br-md bg-indigo-500 text-white"
            : "rounded-bl-md border border-white/10 bg-white/[0.055] text-slate-200"
        }`}
      >
        {!isUser && (
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-indigo-300">
            UserOps AI
          </p>
        )}

        <p className="whitespace-pre-wrap">{message}</p>

        {suggestions.length > 0 && onSuggestion && !action && (
          <div className="mt-4 flex flex-wrap gap-3 border-t border-white/10 pt-4">
            {suggestions.map((suggestion) => {
              const toneClass =
                suggestion.tone === "danger"
                  ? "border-red-400/30 bg-red-400/10 text-red-200 hover:bg-red-400/20"
                  : suggestion.tone === "primary"
                    ? "border-indigo-400/30 bg-indigo-400/10 text-indigo-200 hover:bg-indigo-400/20"
                    : "border-white/15 text-slate-200 hover:bg-white/10";

              return (
                <button
                  key={`${suggestion.label}-${suggestion.value}`}
                  type="button"
                  disabled={actionPending}
                  onClick={() => onSuggestion(suggestion.value)}
                  className={`rounded-lg border px-3.5 py-2 text-xs font-semibold transition disabled:opacity-50 ${toneClass}`}
                >
                  {suggestion.label}
                </button>
              );
            })}
          </div>
        )}

        {action && onAction && (
          <div className="mt-4 flex flex-wrap gap-3 border-t border-white/10 pt-4">
            <button
              type="button"
              disabled={actionPending}
              onClick={() => onAction(action, true)}
              className="rounded-lg bg-red-500 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-red-400 disabled:opacity-50"
            >
              {actionPending ? "Working..." : action.label}
            </button>
            <button
              type="button"
              disabled={actionPending}
              onClick={() => onAction(action, false)}
              className="rounded-lg border border-white/15 px-3.5 py-2 text-xs font-semibold text-slate-200 transition hover:bg-white/10 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}