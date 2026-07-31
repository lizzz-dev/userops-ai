"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import AuthScreen from "@/components/AuthScreen";
import ChatWindow, { type ChatMessage } from "@/components/ChatWindow";
import Header from "@/components/Header";
import MessageInput from "@/components/MessageInput";
import Sidebar from "@/components/Sidebar";
import Toast, { type ToastMessage, type ToastTone } from "@/components/Toast";
import { apiFetch } from "@/lib/api";
import type {
  Account,
  ChatAction,
  ChatApiResponse,
  ChatContext,
  ConversationHistoryResponse,
  ConversationListResponse,
  ConversationSummary,
} from "@/lib/types";


function createMessageId(): string {
  return crypto.randomUUID();
}

function welcomeMessage(name?: string): ChatMessage {
  return {
    id: "welcome-message",
    role: "assistant",
    message: name
      ? `Welcome, ${name}. Speak naturally — I can remember context while we create, find, update, or safely delete users.`
      : "Welcome to UserOps AI.",
    suggestions: [
      { label: "Add a user", value: "We have a new user to add", tone: "primary" },
      { label: "List users", value: "List all users", tone: "default" },
      { label: "Help", value: "What can you do?", tone: "default" },
    ],
  };
}

function formatResponseData(data: ChatApiResponse["data"]): string {
  if (!data) {
    return "";
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return "";
    }

    return data
      .map((item, index) => {
        if ("action" in item) {
          const action = String(item.action).replaceAll("_", " ");
          const target = item.target_email ? ` — ${String(item.target_email)}` : "";
          const time = item.created_at
            ? ` (${new Date(String(item.created_at)).toLocaleString()})`
            : "";
          return `${index + 1}. ${action}${target}${time}`;
        }

        const name = item.name ? String(item.name) : "Unnamed user";
        const email = item.email ? String(item.email) : "No email";
        const id = item.id !== undefined ? `ID ${String(item.id)}` : "";
        const city = item.city ? ` · ${String(item.city)}` : "";
        return `${index + 1}. ${name} — ${email}${id ? ` (${id})` : ""}${city}`;
      })
      .join("\n");
  }

  if ("count" in data) {
    return "";
  }

  const fields: Array<[string, unknown]> = [
    ["ID", data.id],
    ["Name", data.name],
    ["Email", data.email],
    ["Phone", data.phone],
    ["City", data.city],
  ];

  return fields
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([label, value]) => `${label}: ${String(value)}`)
    .join("\n");
}

function responseToMessage(response: ChatApiResponse): ChatMessage {
  const details = formatResponseData(response.data);

  return {
    id: createMessageId(),
    role: "assistant",
    message: details ? `${response.reply}\n\n${details}` : response.reply,
    action: response.action ?? undefined,
    suggestions: response.suggestions ?? [],
  };
}

function deactivateInteractiveMessages(messages: ChatMessage[]): ChatMessage[] {
  return messages.map((message) =>
    message.role === "assistant" &&
    (message.action || (message.suggestions?.length ?? 0) > 0)
      ? { ...message, action: undefined, suggestions: [] }
      : message,
  );
}


function historyToMessages(history: ConversationHistoryResponse): ChatMessage[] {
  const latestAssistant = [...history.messages]
    .reverse()
    .find((item) => item.role === "assistant");

  return history.messages.map((item) => {
    const metadata = item.metadata ?? undefined;
    const details = formatResponseData(metadata?.data ?? null);
    const isLatestAssistant = item.id === latestAssistant?.id;

    return {
      id: `server-${item.id}`,
      role: item.role,
      message:
        item.role === "assistant" && details
          ? `${item.content}\n\n${details}`
          : item.content,
      action:
        isLatestAssistant && history.context.pending_action
          ? metadata?.action ?? undefined
          : undefined,
      suggestions: isLatestAssistant ? metadata?.suggestions ?? [] : [],
    };
  });
}

function successToastForResponse(response: ChatApiResponse): string | null {
  if (response.status !== "success") {
    return null;
  }

  const operation = response.interpretation?.operation;

  if (operation === "create") {
    return "User created successfully.";
  }
  if (operation === "update") {
    return "User updated successfully.";
  }
  if (operation === "delete") {
    return "User deleted successfully.";
  }

  return null;
}

export default function Home() {
  const [account, setAccount] = useState<Account | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage()]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [context, setContext] = useState<ChatContext | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null);
  const [renamingConversationId, setRenamingConversationId] = useState<string | null>(null);
  const [pendingActionId, setPendingActionId] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const showToast = useCallback((message: string, tone: ToastTone = "info") => {
    setToast({ id: Date.now(), message, tone });
  }, []);

  const dismissToast = useCallback(() => {
    setToast(null);
  }, []);

  const conversationKey = useMemo(
    () => (account ? `userops-conversation-${account.id}` : null),
    [account],
  );

  const fetchConversationHistory = useCallback(
    async (selectedConversationId: string) => {
      const history = await apiFetch<ConversationHistoryResponse>(
        `/chat/conversations/${selectedConversationId}`,
      );

      setConversationId(history.conversation_id);
      setContext(history.context);
      setPendingActionId(null);

      const restoredMessages = historyToMessages(history);
      setMessages(
        restoredMessages.length > 0
          ? restoredMessages
          : [welcomeMessage(account?.full_name.split(" ")[0])],
      );

      if (conversationKey) {
        window.localStorage.setItem(
          conversationKey,
          history.conversation_id,
        );
      }
    },
    [account, conversationKey],
  );

  const refreshConversations = useCallback(async () => {
    if (!account) {
      setConversations([]);
      return [];
    }

    setIsLoadingConversations(true);

    try {
      const response = await apiFetch<ConversationListResponse>(
        "/chat/conversations",
      );
      setConversations(response.conversations);
      return response.conversations;
    } catch {
      setConversations([]);
      return [];
    } finally {
      setIsLoadingConversations(false);
    }
  }, [account]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }

      const target = event.target as HTMLElement | null;
      const isEditing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      if (isEditing) {
        return;
      }

      event.preventDefault();
      inputRef.current?.focus();
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const currentAccount = await apiFetch<Account>("/auth/me");
        setAccount(currentAccount);
      } catch {
        setAccount(null);
      } finally {
        setIsCheckingSession(false);
      }
    };

    void restoreSession();
  }, []);

  useEffect(() => {
    if (!account || !conversationKey) {
      return;
    }

    let cancelled = false;

    const initializeConversations = async () => {
      setIsLoadingConversations(true);

      try {
        const response = await apiFetch<ConversationListResponse>(
          "/chat/conversations",
        );

        if (cancelled) {
          return;
        }

        setConversations(response.conversations);

        const storedId = window.localStorage.getItem(conversationKey);
        const storedConversationExists = response.conversations.some(
          (conversation) => conversation.conversation_id === storedId,
        );

        if (storedId && storedConversationExists) {
          try {
            await fetchConversationHistory(storedId);
            return;
          } catch {
            window.localStorage.removeItem(conversationKey);
          }
        }

        if (!cancelled) {
          setConversationId(null);
          setContext(null);
          setPendingActionId(null);
          setMessages([welcomeMessage(account.full_name.split(" ")[0])]);
        }
      } catch {
        if (!cancelled) {
          setConversations([]);
          setConversationId(null);
          setContext(null);
          setMessages([welcomeMessage(account.full_name.split(" ")[0])]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingConversations(false);
        }
      }
    };

    void initializeConversations();

    return () => {
      cancelled = true;
    };
  }, [account, conversationKey, fetchConversationHistory]);

  const handleAuthenticated = (authenticatedAccount: Account) => {
    setAccount(authenticatedAccount);
    setConversationId(null);
    setConversations([]);
    setContext(null);
    setPendingActionId(null);
    setMessages([welcomeMessage(authenticatedAccount.full_name.split(" ")[0])]);
  };

  const handleLogout = async () => {
    try {
      await apiFetch<void>("/auth/logout", { method: "POST" });
    } finally {
      setAccount(null);
      setConversationId(null);
      setConversations([]);
      setContext(null);
      setPendingActionId(null);
      setMessages([welcomeMessage()]);
    }
  };

  const resetConversation = () => {
    if (conversationKey) {
      window.localStorage.removeItem(conversationKey);
    }

    setConversationId(null);
    setContext(null);
    setPendingActionId(null);
    setMessages([welcomeMessage(account?.full_name.split(" ")[0])]);
  };

  const selectConversation = async (selectedConversationId: string) => {
    if (selectedConversationId === conversationId || isLoading) {
      return;
    }

    setIsLoading(true);

    try {
      await fetchConversationHistory(selectedConversationId);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          message:
            error instanceof Error
              ? `I could not open that conversation. ${error.message}`
              : "I could not open that conversation.",
        },
      ]);
      await refreshConversations();
    } finally {
      setIsLoading(false);
    }
  };

  const deleteConversation = async (selectedConversationId: string) => {
    const selectedConversation = conversations.find(
      (conversation) =>
        conversation.conversation_id === selectedConversationId,
    );

    const confirmed = window.confirm(
      `Delete “${selectedConversation?.title ?? "this conversation"}”? This cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    setDeletingConversationId(selectedConversationId);

    try {
      await apiFetch<void>(
        `/chat/conversations/${selectedConversationId}/permanent`,
        { method: "DELETE" },
      );

      setConversations((current) =>
        current.filter(
          (conversation) =>
            conversation.conversation_id !== selectedConversationId,
        ),
      );

      showToast("Conversation deleted.", "success");

      if (selectedConversationId === conversationId) {
        if (conversationKey) {
          window.localStorage.removeItem(conversationKey);
        }

        setConversationId(null);
        setContext(null);
        setPendingActionId(null);
        setMessages([welcomeMessage(account?.full_name.split(" ")[0])]);
      }
    } catch (error) {
      showToast(
        error instanceof Error
          ? `Conversation could not be deleted. ${error.message}`
          : "Conversation could not be deleted.",
        "error",
      );
      await refreshConversations();
    } finally {
      setDeletingConversationId(null);
    }
  };


  const renameConversation = async (
    selectedConversationId: string,
    title: string,
  ) => {
    const cleanedTitle = title.trim().replace(/\s+/g, " ");

    if (!cleanedTitle) {
      showToast("Conversation title cannot be empty.", "error");
      return;
    }

    setRenamingConversationId(selectedConversationId);

    try {
      const renamedConversation = await apiFetch<ConversationSummary>(
        `/chat/conversations/${selectedConversationId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ title: cleanedTitle }),
        },
      );

      setConversations((current) =>
        current.map((conversation) =>
          conversation.conversation_id === selectedConversationId
            ? renamedConversation
            : conversation,
        ),
      );
      showToast("Conversation renamed.", "success");
    } catch (error) {
      showToast(
        error instanceof Error
          ? `Conversation could not be renamed. ${error.message}`
          : "Conversation could not be renamed.",
        "error",
      );
      await refreshConversations();
    } finally {
      setRenamingConversationId(null);
    }
  };

  const appendAssistantResponse = (response: ChatApiResponse) => {
    if (response.conversation_id) {
      setConversationId(response.conversation_id);

      if (conversationKey) {
        window.localStorage.setItem(
          conversationKey,
          response.conversation_id,
        );
      }
    }

    setContext(response.context ?? null);
    setMessages((current) => [
      ...deactivateInteractiveMessages(current),
      responseToMessage(response),
    ]);

    const successMessage = successToastForResponse(response);
    if (successMessage) {
      showToast(successMessage, "success");
    }

    void refreshConversations();
  };

  const sendMessage = async (message: string) => {
    setMessages((current) => [
      ...current,
      { id: createMessageId(), role: "user", message },
    ]);
    setIsLoading(true);

    try {
      const response = await apiFetch<ChatApiResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
      });
      appendAssistantResponse(response);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? `I could not complete the request. ${error.message}`
          : "I could not complete the request.";

      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          message: errorMessage,
        },
      ]);
      showToast(errorMessage, "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAction = async (
    messageId: string,
    action: ChatAction,
    confirm: boolean,
  ) => {
    setPendingActionId(messageId);

    try {
      const response = await apiFetch<ChatApiResponse>("/chat/confirm", {
        method: "POST",
        body: JSON.stringify({
          token: action.token,
          confirm,
          conversation_id: conversationId,
        }),
      });

      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? { ...message, action: undefined, suggestions: [] }
            : message,
        ),
      );
      appendAssistantResponse(response);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "The confirmation could not be completed.";

      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          message: errorMessage,
        },
      ]);
      showToast(errorMessage, "error");
    } finally {
      setPendingActionId(null);
    }
  };

  if (isCheckingSession) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-950 text-white">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-pulse rounded-2xl bg-indigo-500" />
          <p className="text-sm text-slate-400">Restoring your secure session...</p>
        </div>
      </main>
    );
  }

  if (!account) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  return (
    <>
      <Toast toast={toast} onDismiss={dismissToast} />
      <div className="flex h-screen overflow-hidden bg-slate-950 text-white">
      <Sidebar
        account={account}
        conversations={conversations}
        activeConversationId={conversationId}
        isLoadingConversations={isLoadingConversations}
        deletingConversationId={deletingConversationId}
        renamingConversationId={renamingConversationId}
        onNewConversation={resetConversation}
        onSelectConversation={(selectedConversationId) =>
          void selectConversation(selectedConversationId)
        }
        onDeleteConversation={(selectedConversationId) =>
          void deleteConversation(selectedConversationId)
        }
        onRenameConversation={(selectedConversationId, title) =>
          void renameConversation(selectedConversationId, title)
        }
        onPrompt={(prompt) => void sendMessage(prompt)}
        onLogout={() => void handleLogout()}
      />

      <section className="flex min-h-0 min-w-0 flex-1 flex-col">
        <Header onLogout={() => void handleLogout()} />
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          pendingActionId={pendingActionId}
          context={context}
          onAction={(messageId, action, confirm) =>
            void handleAction(messageId, action, confirm)
          }
          onSuggestion={(value) => void sendMessage(value)}
        />
        <MessageInput
          inputRef={inputRef}
          onSend={sendMessage}
          disabled={isLoading || pendingActionId !== null}
        />
      </section>
      </div>
    </>
  );
}