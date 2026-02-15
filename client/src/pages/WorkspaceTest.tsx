import { useState } from "react";
import type { Session } from "@supabase/supabase-js";

import TokenMeter from "../components/usage/TokenMeter";
import { useUsage } from "../hooks/useUsage";
import { apiAuthMe, apiCreateWorkspace, apiGetWorkspaceMe, ApiError } from "../lib/api";

type WorkspaceTestProps = {
  session: Session;
};

export default function WorkspaceTest({ session }: WorkspaceTestProps) {
  const [workspaceName, setWorkspaceName] = useState("My Workspace");
  const [authMeResponse, setAuthMeResponse] = useState<unknown>(null);
  const [createWorkspaceResponse, setCreateWorkspaceResponse] = useState<unknown>(null);
  const [workspaceMeResponse, setWorkspaceMeResponse] = useState<unknown>(null);
  const [status, setStatus] = useState("");

  const token = session.access_token;
  const { usage, loading: usageLoading, error: usageError, refresh: refreshUsage } = useUsage(token);

  const parseError = (error: unknown) => {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return `401 Unauthorized: ${JSON.stringify(error.payload, null, 2)}`;
      }
      if (error.status === 409) {
        return `409 Conflict: ${JSON.stringify(error.payload, null, 2)}`;
      }
      return `${error.status}: ${JSON.stringify(error.payload, null, 2)}`;
    }

    return String(error);
  };

  const handleAuthMe = async () => {
    setStatus("Calling /auth/me...");
    try {
      const data = await apiAuthMe(token);
      setAuthMeResponse(data);
      setStatus("/auth/me success.");
    } catch (error) {
      setAuthMeResponse({ error: parseError(error) });
      setStatus("/auth/me failed.");
    }
  };

  const handleCreateWorkspace = async () => {
    setStatus("Calling POST /workspaces...");
    try {
      const data = await apiCreateWorkspace(token, workspaceName);
      setCreateWorkspaceResponse(data);
      setStatus("POST /workspaces success.");
    } catch (error) {
      setCreateWorkspaceResponse({ error: parseError(error) });
      setStatus("POST /workspaces failed.");
    }
  };

  const handleWorkspaceMe = async () => {
    setStatus("Calling /workspaces/me...");
    try {
      const data = await apiGetWorkspaceMe(token);
      setWorkspaceMeResponse(data);
      setStatus("/workspaces/me success.");
    } catch (error) {
      setWorkspaceMeResponse({ error: parseError(error) });
      setStatus("/workspaces/me failed.");
    }
  };

  return (
    <main>
      <h1>Workspace Endpoint Test</h1>
      <p>{status}</p>

      <section>
        <h2>Auth</h2>
        <button onClick={handleAuthMe}>Call /auth/me</button>
        <pre>{JSON.stringify(authMeResponse, null, 2)}</pre>
      </section>

      <section>
        <h2>Create Workspace</h2>
        <input
          value={workspaceName}
          onChange={(e) => setWorkspaceName(e.target.value)}
          placeholder="Workspace name"
        />
        <button onClick={handleCreateWorkspace}>Create workspace</button>
        <pre>{JSON.stringify(createWorkspaceResponse, null, 2)}</pre>
      </section>

      <section>
        <h2>Workspace Me</h2>
        <button onClick={handleWorkspaceMe}>Call /workspaces/me</button>
        <pre>{JSON.stringify(workspaceMeResponse, null, 2)}</pre>
      </section>

      <section>
        <h2>Usage Today</h2>
        <button onClick={() => void refreshUsage()}>Refresh /usage/today</button>
        <TokenMeter usage={usage} loading={usageLoading} error={usageError} />
      </section>
    </main>
  );
}
