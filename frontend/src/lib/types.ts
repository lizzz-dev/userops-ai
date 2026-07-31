export type Account = {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
  updated_at: string;
};

export type UserRecord = {
  id: number;
  name: string | null;
  email: string;
  phone: string | null;
  city: string | null;
  created_at?: string;
  updated_at?: string;
};

export type ChatStatus =
  | "success"
  | "collecting_fields"
  | "invalid"
  | "not_found"
  | "needs_clarification"
  | "needs_confirmation"
  | "cancelled"
  | "error";

export type ConversationStatus =
  | "idle"
  | "collecting_fields"
  | "awaiting_clarification"
  | "awaiting_confirmation"
  | "completed"
  | "cancelled";

export type AssistantIntent =
  | "start_operation"
  | "provide_information"
  | "select_candidate"
  | "confirm"
  | "cancel"
  | "switch_operation"
  | "greeting"
  | "help"
  | "ask_context"
  | "unknown";

export type AssistantOperation =
  | "create"
  | "read"
  | "update"
  | "delete"
  | "list"
  | "count"
  | "activity"
  | "none";

export type AssistantReferenceType =
  | "email"
  | "name"
  | "id"
  | "current_user"
  | "current_draft"
  | "candidate"
  | "none";

export type AssistantControlAction =
  | "continue"
  | "confirm"
  | "cancel"
  | "skip"
  | "reset"
  | "none";

export type AssistantFieldName =
  | "name"
  | "email"
  | "phone"
  | "city"
  | "none";

export type AssistantFields = {
  name: string | null;
  email: string | null;
  phone: string | null;
  city: string | null;
};

export type AssistantInterpretation = {
  intent: AssistantIntent;
  operation: AssistantOperation;
  reference_type: AssistantReferenceType;
  user_id: number | null;
  ordinal: number | null;
  candidate_hint: string | null;
  requested_field: AssistantFieldName;
  fields: AssistantFields;
  control: AssistantControlAction;
  confidence: number;
  explanation: string;
};

export type ChatAction = {
  type: "confirm_delete";
  token: string;
  label: string;
  destructive: boolean;
};

export type ChatSuggestion = {
  label: string;
  value: string;
  tone: "default" | "primary" | "danger";
};

export type DraftFields = {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  city?: string | null;
};

export type ChatContext = {
  status: ConversationStatus;
  current_intent: string | null;
  awaiting_field: string | null;
  selected_user_id: number | null;
  selected_user: UserRecord | null;
  draft_fields: DraftFields;
  candidate_count: number;
  pending_action: string | null;
  ai_mode: "openai" | "fallback";
};

export type ChatData =
  | Record<string, unknown>
  | Array<Record<string, unknown>>
  | null;

export type ChatApiResponse = {
  status: ChatStatus;
  reply: string;
  conversation_id: string | null;
  data: ChatData;
  action: ChatAction | null;
  suggestions: ChatSuggestion[];
  context: ChatContext | null;
  interpretation: AssistantInterpretation | null;
};

export type ConversationMessageMetadata = {
  status?: ChatStatus;
  data?: ChatData;
  action?: ChatAction | null;
  suggestions?: ChatSuggestion[];
  context?: ChatContext | null;
  interpretation?: AssistantInterpretation | null;
};

export type ConversationHistoryMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  metadata: ConversationMessageMetadata | null;
  created_at: string;
};

export type ConversationHistoryResponse = {
  conversation_id: string;
  context: ChatContext;
  messages: ConversationHistoryMessage[];
};

export type ConversationSummary = {
  conversation_id: string;
  title: string;
  preview: string;
  message_count: number;
  created_at: string;
  updated_at: string;
};

export type ConversationListResponse = {
  conversations: ConversationSummary[];
};


export type ConversationRenameRequest = {
  title: string;
};