import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { ApiError, apiCreateWorkspace, apiGetWorkspaceMe } from "../lib/api";

export default function WorkspaceGate() {
  const { accessToken } = useAuth();
  const navigate = useNavigate();

  const [checking, setChecking] = useState(true);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    let active = true;

    const loadWorkspace = async () => {
      setChecking(true);
      setError(null);
      try {
        await apiGetWorkspaceMe(accessToken);
        if (active) {
          navigate("/app/upload", { replace: true });
        }
      } catch (err) {
        if (!active) {
          return;
        }

        if (err instanceof ApiError && err.status === 404) {
          setChecking(false);
          return;
        }

        setError(err instanceof Error ? err.message : "Unable to load workspace.");
        setChecking(false);
      }
    };

    void loadWorkspace();

    return () => {
      active = false;
    };
  }, [accessToken, navigate]);

  const onCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!accessToken) {
      return;
    }

    const trimmed = name.trim();
    if (!trimmed) {
      setError("Workspace name is required.");
      return;
    }

    setCreating(true);
    setError(null);

    try {
      await apiCreateWorkspace(accessToken, trimmed);
      navigate("/app/upload", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        navigate("/app/upload", { replace: true });
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to create workspace.");
    } finally {
      setCreating(false);
    }
  };

  if (checking) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-white px-4">
        <div className="inline-flex items-center gap-2 rounded-xl border border-app-border bg-app-surface px-4 py-3 text-sm text-app-muted">
          <span className="spinner" aria-hidden="true" />
          Checking workspace...
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-white px-4 py-10">
      <section className="w-full max-w-lg rounded-2xl border border-app-border bg-white p-8 shadow-card">
        <p className="text-xs uppercase tracking-[0.1em] text-app-muted">Workspace setup</p>
        <h1 className="mt-3 text-3xl font-semibold text-app-text">Create your workspace</h1>
        <p className="mt-2 text-sm text-app-muted">You need one workspace before uploading documents.</p>

        <form className="mt-8 space-y-4" onSubmit={onCreate}>
          <div>
            <label htmlFor="workspace-name" className="mb-1.5 block text-sm font-medium text-app-text">
              Workspace name
            </label>
            <input
              id="workspace-name"
              className="app-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Acme Research"
              maxLength={120}
              required
            />
          </div>

          {error ? <p className="text-sm text-app-danger">{error}</p> : null}

          <button type="submit" className="btn-primary" disabled={creating}>
            {creating ? "Creating workspace..." : "Create workspace"}
          </button>
        </form>
      </section>
    </main>
  );
}
