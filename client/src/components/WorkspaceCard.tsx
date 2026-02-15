import { useState } from "react";
import type { FormEvent } from "react";

type Workspace = {
  id: string;
  name: string;
};

type WorkspaceCardProps = {
  workspace: Workspace | null;
  loading: boolean;
  error: string | null;
  creating: boolean;
  onCreate: (name: string) => Promise<void>;
};

export default function WorkspaceCard({
  workspace,
  loading,
  error,
  creating,
  onCreate,
}: WorkspaceCardProps) {
  const [name, setName] = useState("My Workspace");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      return;
    }
    await onCreate(name.trim());
  };

  return (
    <section className="rounded-xl border border-app-border bg-app-surface p-4 shadow-card">
      <h3 className="text-sm font-medium text-app-text">Workspace</h3>

      {loading ? (
        <div className="mt-4 space-y-3">
          <div className="skeleton h-4 w-48 rounded" />
          <div className="skeleton h-4 w-64 rounded" />
          <div className="skeleton h-10 w-full rounded-lg" />
        </div>
      ) : null}

      {!loading && workspace ? (
        <div className="mt-4 space-y-2 text-sm">
          <div>
            <p className="text-app-muted">Name</p>
            <p className="font-medium text-app-text">{workspace.name}</p>
          </div>
          <div>
            <p className="text-app-muted">Workspace ID</p>
            <p className="break-all font-mono text-xs text-app-text">{workspace.id}</p>
          </div>
        </div>
      ) : null}

      {!loading && !workspace ? (
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label htmlFor="workspace-name" className="mb-1 block text-sm text-app-muted">
              Workspace name
            </label>
            <input
              id="workspace-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={255}
              className="w-full rounded-lg border border-app-border bg-app-elevated px-3 py-2 text-sm text-app-text outline-none ring-0 transition placeholder:text-app-muted/80 focus:border-app-accent focus:ring-2 focus:ring-app-accent/40"
              placeholder="My Workspace"
              required
            />
          </div>
          <button
            type="submit"
            disabled={creating}
            className="inline-flex items-center gap-2 rounded-lg bg-app-accent px-4 py-2 text-sm font-semibold text-black transition hover:bg-app-accentSoft disabled:cursor-not-allowed disabled:opacity-60"
          >
            {creating ? <span className="spinner" aria-hidden="true" /> : null}
            {creating ? "Creating..." : "Create Workspace"}
          </button>
        </form>
      ) : null}

      {error ? <p className="mt-3 text-sm text-red-400">{error}</p> : null}
    </section>
  );
}
