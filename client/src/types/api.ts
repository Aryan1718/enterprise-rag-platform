export type ApiErrorPayload = {
  detail?: string | { message?: string; workspace_id?: string };
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
};

export type AuthMeResponse = {
  user_id: string;
  email: string | null;
  role: string | null;
};

export type UsageTodayResponse = {
  used?: number;
  reserved?: number;
  tokens_used?: number;
  tokens_reserved?: number;
  limit: number;
  remaining: number;
  resets_at: string;
};

export type WorkspaceResponse = {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
};

export type WorkspaceMeResponse = {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  document_count: number;
  documents_by_status: Record<string, number>;
  usage_today: UsageTodayResponse;
};

export type ApiResponseError = {
  message: string;
  status: number;
  payload: unknown;
};
