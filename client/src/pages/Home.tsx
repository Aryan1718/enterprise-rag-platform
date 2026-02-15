import { useCallback, useEffect, useMemo, useState } from "react";

import DiagnosticsAccordion from "../components/DiagnosticsAccordion";
import StatsCard from "../components/StatsCard";
import Toast, { type ToastState } from "../components/Toast";
import UsageProgress from "../components/UsageProgress";
import WorkspaceCard from "../components/WorkspaceCard";
import { useAuth } from "../context/AuthContext";
import { apiCreateWorkspace, apiGetAuthMe, apiGetWorkspaceMe, ApiError } from "../lib/api";
import { appName } from "../styles/theme";
import type { UsageTodayResponse, WorkspaceMeResponse } from "../types/api";

type NormalizedUsage = {
  used: number;
  reserved: number;
  limit: number;
  remaining: number;
  resetsAt: string;
};

function normalizeUsage(usage: UsageTodayResponse | undefined): NormalizedUsage {
  const used = usage?.used ?? usage?.tokens_used ?? 0;
  const reserved = usage?.reserved ?? usage?.tokens_reserved ?? 0;
  const limit = usage?.limit ?? 100000;
  const remaining = usage?.remaining ?? Math.max(0, limit - used - reserved);
  const resetsAt = usage?.resets_at ?? "";

  return { used, reserved, limit, remaining, resetsAt };
}

function parseApiError(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.status}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed.";
}

export default function Home() {
  const { user, access_token: accessToken, signOut } = useAuth();
  const [workspace, setWorkspace] = useState<WorkspaceMeResponse | null>(null);
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);
  const [authMeJson, setAuthMeJson] = useState<string>("{\n  \"message\": \"No diagnostics fetched yet\"\n}");
  const [toast, setToast] = useState<ToastState | null>(null);

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ id: Date.now(), message, type });
  }, []);

  const fetchWorkspace = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setWorkspaceLoading(true);
    setWorkspaceError(null);
    try {
      const data = await apiGetWorkspaceMe(accessToken);
      setWorkspace(data);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setWorkspace(null);
      } else {
        setWorkspaceError(parseApiError(error));
      }
    } finally {
      setWorkspaceLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void fetchWorkspace();
  }, [fetchWorkspace]);

  const handleCreateWorkspace = async (name: string) => {
    if (!accessToken) {
      setWorkspaceError("Missing access token.");
      showToast("Missing access token.", "error");
      return;
    }

    setCreateLoading(true);
    setWorkspaceError(null);

    try {
      await apiCreateWorkspace(accessToken, name);
      await fetchWorkspace();
      showToast("Workspace created.", "success");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        await fetchWorkspace();
        showToast("Workspace already exists. Loaded existing workspace.", "success");
      } else {
        const message = parseApiError(error);
        setWorkspaceError(message);
        showToast(message, "error");
      }
    } finally {
      setCreateLoading(false);
    }
  };

  const handleAuthMe = async () => {
    if (!accessToken) {
      return;
    }

    setDiagnosticsLoading(true);
    try {
      const data = await apiGetAuthMe(accessToken);
      setAuthMeJson(JSON.stringify(data, null, 2));
    } catch (error) {
      const message = parseApiError(error);
      setAuthMeJson(JSON.stringify({ error: message }, null, 2));
      showToast(message, "error");
    } finally {
      setDiagnosticsLoading(false);
    }
  };

  const usage = useMemo(() => normalizeUsage(workspace?.usage_today), [workspace]);
  const workspaceJson = useMemo(
    () => JSON.stringify(workspace ?? { message: "No workspace loaded" }, null, 2),
    [workspace],
  );

  return (
    <main className="min-h-screen bg-app-bg px-4 py-6">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
        <header className="rounded-xl border border-app-border bg-app-surface/95 p-4 shadow-card backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-app-accent text-base font-bold text-black">
                ER
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-app-muted">{appName}</p>
                <h1 className="text-xl font-semibold text-app-text">Workspace Home</h1>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="rounded-full border border-app-accent/60 bg-app-elevated px-3 py-1.5 text-sm text-app-text">
                {user?.email ?? "Unknown user"}
              </div>
              <button
                type="button"
                onClick={() => void signOut()}
                className="rounded-lg border border-app-accent/60 bg-app-elevated px-3 py-2 text-sm text-app-text transition hover:border-app-accent hover:text-app-accent"
              >
                Sign out
              </button>
            </div>
          </div>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatsCard label="Used" value={usage.used.toLocaleString()} />
          <StatsCard label="Reserved" value={usage.reserved.toLocaleString()} />
          <StatsCard label="Remaining" value={usage.remaining.toLocaleString()} />
          <StatsCard label="Daily Limit" value={usage.limit.toLocaleString()} helper="v1 fixed limit" />
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <WorkspaceCard
            workspace={workspace ? { id: workspace.id, name: workspace.name } : null}
            loading={workspaceLoading}
            error={workspaceError}
            creating={createLoading}
            onCreate={handleCreateWorkspace}
          />
          <UsageProgress
            used={usage.used}
            reserved={usage.reserved}
            remaining={usage.remaining}
            limit={usage.limit}
            resetsAt={usage.resetsAt}
            loading={workspaceLoading}
          />
        </section>

        <DiagnosticsAccordion
          authMeJson={authMeJson}
          workspaceJson={workspaceJson}
          loadingAuthMe={diagnosticsLoading}
          loadingWorkspace={workspaceLoading}
          onFetchAuthMe={handleAuthMe}
          onRefreshWorkspace={fetchWorkspace}
        />
      </div>

      <Toast toast={toast} onClose={() => setToast(null)} />
    </main>
  );
}
