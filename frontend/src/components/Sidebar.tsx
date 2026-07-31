"use client";

import { useState } from "react";

import BrandLogo from "./BrandLogo";
import type { Account, ConversationSummary } from "@/lib/types";


const exampleCommands = [
  "We have a new user called Sara",
  "Show me Ali",
  "She moved to Islamabad",
  "How many users are there?",
  "Show recent activity",
];

type SidebarProps = {
  account: Account;
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  isLoadingConversations: boolean;
  deletingConversationId: string | null;
  renamingConversationId: string | null;
  onNewConversation: () => void;
  onSelectConversation: (conversationId: string) => void;
  onDeleteConversation: (conversationId: string) => void;
  onRenameConversation: (conversationId: string, title: string) => void;
  onPrompt: (prompt: string) => void;
  onLogout: () => void;
};

function formatConversationDate(value: string): string {
  const date = new Date(value);
  const today = new Date();

  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return date.toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
}

export default function Sidebar({
  account,
  conversations,
  activeConversationId,
  isLoadingConversations,
  deletingConversationId,
  renamingConversationId,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onPrompt,
  onLogout,
}: SidebarProps) {
  const initial = account.full_name.charAt(0).toUpperCase();
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  const startEditing = (conversation: ConversationSummary) => {
    setEditingConversationId(conversation.conversation_id);
    setEditingTitle(conversation.title);
  };

  const cancelEditing = () => {
    setEditingConversationId(null);
    setEditingTitle("");
  };

  const saveEditing = () => {
    if (!editingConversationId) {
      return;
    }

    const cleanedTitle = editingTitle.trim().replace(/\s+/g, " ");
    if (!cleanedTitle) {
      return;
    }

    onRenameConversation(editingConversationId, cleanedTitle);
    cancelEditing();
  };

  return (
    <aside className="hidden h-screen w-72 shrink-0 flex-col border-r border-white/10 bg-slate-950 p-4 lg:flex">
      <div className="mb-7">
        <BrandLogo showText />
      </div>

      <button
        type="button"
        onClick={onNewConversation}
        className="mb-5 rounded-xl bg-indigo-500 px-4 py-3 font-medium text-white transition hover:bg-indigo-400"
      >
        + New conversation
      </button>

      <div className="mb-5">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recent conversations
          </p>
          {conversations.length > 0 ? (
            <span className="text-xs text-slate-600">{conversations.length}</span>
          ) : null}
        </div>

        <div className="max-h-64 space-y-1 overflow-y-auto pr-1">
          {isLoadingConversations ? (
            <div className="space-y-2 py-1">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-14 animate-pulse rounded-lg bg-white/5" />
              ))}
            </div>
          ) : conversations.length > 0 ? (
            conversations.map((conversation) => {
              const isActive = conversation.conversation_id === activeConversationId;
              const isEditing = editingConversationId === conversation.conversation_id;
              const isRenaming = renamingConversationId === conversation.conversation_id;

              return (
                <div key={conversation.conversation_id} className="group relative">
                  {isEditing ? (
                    <div className="rounded-lg border border-indigo-400/30 bg-indigo-500/10 p-2">
                      <input
                        autoFocus
                        value={editingTitle}
                        maxLength={80}
                        disabled={isRenaming}
                        onChange={(event) => setEditingTitle(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            saveEditing();
                          }
                          if (event.key === "Escape") {
                            cancelEditing();
                          }
                        }}
                        className="w-full rounded-md border border-white/10 bg-slate-900 px-2 py-1.5 text-sm text-white outline-none focus:border-indigo-400"
                      />
                      <div className="mt-2 flex justify-end gap-1">
                        <button
                          type="button"
                          onClick={cancelEditing}
                          className="rounded px-2 py-1 text-xs text-slate-400 hover:bg-white/5 hover:text-white"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          disabled={!editingTitle.trim() || isRenaming}
                          onClick={saveEditing}
                          className="rounded bg-indigo-500 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isRenaming ? "Saving..." : "Save"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => onSelectConversation(conversation.conversation_id)}
                        aria-current={isActive ? "page" : undefined}
                        className={`w-full rounded-lg border px-3 py-2.5 pr-20 text-left transition ${
                          isActive
                            ? "border-indigo-400/30 bg-indigo-500/10 text-white"
                            : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/5 hover:text-white"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <p className="min-w-0 flex-1 truncate text-sm font-medium">
                            {conversation.title}
                          </p>
                          <span className="shrink-0 text-[10px] text-slate-500">
                            {formatConversationDate(conversation.updated_at)}
                          </span>
                        </div>
                        <p className="mt-1 truncate text-xs text-slate-500">
                          {conversation.preview}
                        </p>
                      </button>

                      <div className="absolute right-2 top-2.5 flex gap-1 opacity-0 transition focus-within:opacity-100 group-hover:opacity-100">
                        <button
                          type="button"
                          title="Rename conversation"
                          aria-label={`Rename ${conversation.title}`}
                          disabled={isRenaming || deletingConversationId === conversation.conversation_id}
                          onClick={(event) => {
                            event.stopPropagation();
                            startEditing(conversation);
                          }}
                          className="grid h-7 w-7 place-items-center rounded-md text-slate-500 hover:bg-indigo-500/10 hover:text-indigo-300 disabled:cursor-wait"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
                            <path d="M4 20h4l10.5-10.5a2.12 2.12 0 0 0-3-3L5 17v3Z" />
                            <path d="m13.5 8.5 3 3" />
                          </svg>
                        </button>

                        <button
                          type="button"
                          title="Delete conversation"
                          aria-label={`Delete ${conversation.title}`}
                          disabled={deletingConversationId === conversation.conversation_id || isRenaming}
                          onClick={(event) => {
                            event.stopPropagation();
                            onDeleteConversation(conversation.conversation_id);
                          }}
                          className="grid h-7 w-7 place-items-center rounded-md text-slate-500 hover:bg-red-500/10 hover:text-red-300 disabled:cursor-wait"
                        >
                          {deletingConversationId === conversation.conversation_id ? (
                            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                          ) : (
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
                              <path d="M4 7h16" />
                              <path d="M9 7V4h6v3" />
                              <path d="m6 7 1 13h10l1-13" />
                              <path d="M10 11v5M14 11v5" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-5 text-center">
              <div className="mx-auto mb-2 grid h-9 w-9 place-items-center rounded-xl bg-indigo-500/10 text-indigo-300">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4" aria-hidden="true">
                  <path d="M5 5h14v10H8l-3 3V5Z" />
                  <path d="M8 9h8M8 12h5" />
                </svg>
              </div>
              <p className="text-xs font-medium text-slate-300">No conversations yet</p>
              <p className="mt-1 text-[11px] leading-5 text-slate-500">
                Send your first message and it will be saved here automatically.
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Try a command
        </p>

        <div className="space-y-2">
          {exampleCommands.map((command) => (
            <button
              type="button"
              key={command}
              onClick={() => onPrompt(command)}
              className="w-full rounded-lg border border-transparent px-3 py-3 text-left text-sm leading-5 text-slate-400 transition hover:border-white/10 hover:bg-white/5 hover:text-white"
            >
              {command}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-sm font-bold text-indigo-300">
            {initial}
          </div>

          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-white">{account.full_name}</p>
            <p className="truncate text-xs text-slate-400">{account.email}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onLogout}
          className="mt-3 w-full rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}