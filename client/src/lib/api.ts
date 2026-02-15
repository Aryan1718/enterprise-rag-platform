import type { AuthMeResponse, UsageTodayResponse, WorkspaceMeResponse, WorkspaceResponse } from "../types/api";

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

let unauthorizedHandler: (() => void | Promise<void>) | null = null;

export function setUnauthorizedHandler(handler: (() => void | Promise<void>) | null): void {
  unauthorizedHandler = handler;
}

function parsePayloadMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (typeof detail === "object" && detail !== null && "message" in detail) {
      return String((detail as { message: unknown }).message);
    }
  }

  if (typeof payload === "object" && payload !== null && "error" in payload) {
    const error = (payload as { error: unknown }).error;
    if (typeof error === "object" && error !== null && "message" in error) {
      return String((error as { message: unknown }).message);
    }
  }

  return fallback;
}

async function apiRequest<T>(path: string, token: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options?.headers ?? {}),
    },
  });

  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler) {
      await unauthorizedHandler();
    }

    const message = parsePayloadMessage(payload, `Request failed with status ${response.status}`);
    throw new ApiError(message, response.status, payload);
  }

  return payload as T;
}

export function apiGetAuthMe(token: string): Promise<AuthMeResponse> {
  return apiRequest<AuthMeResponse>("/auth/me", token, { method: "GET" });
}

export function apiAuthMe(token: string): Promise<AuthMeResponse> {
  return apiGetAuthMe(token);
}

export function apiCreateWorkspace(token: string, name: string): Promise<WorkspaceResponse> {
  return apiRequest<WorkspaceResponse>("/workspaces", token, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function apiGetWorkspaceMe(token: string): Promise<WorkspaceMeResponse> {
  return apiRequest<WorkspaceMeResponse>("/workspaces/me", token, { method: "GET" });
}

export function apiGetUsageToday(token: string): Promise<UsageTodayResponse> {
  return apiRequest<UsageTodayResponse>("/usage/today", token, { method: "GET" });
}
