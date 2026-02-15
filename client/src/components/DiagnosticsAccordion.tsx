type DiagnosticsAccordionProps = {
  authMeJson: string;
  workspaceJson: string;
  loadingAuthMe: boolean;
  loadingWorkspace: boolean;
  onFetchAuthMe: () => Promise<void>;
  onRefreshWorkspace: () => Promise<void>;
};

export default function DiagnosticsAccordion({
  authMeJson,
  workspaceJson,
  loadingAuthMe,
  loadingWorkspace,
  onFetchAuthMe,
  onRefreshWorkspace,
}: DiagnosticsAccordionProps) {
  return (
    <details className="group rounded-xl border border-app-border bg-app-surface p-4 shadow-card">
      <summary className="cursor-pointer list-none text-sm font-medium text-app-text">
        <span className="inline-flex items-center gap-2">
          Diagnostics
          <span className="text-xs text-app-muted transition group-open:rotate-90">▶</span>
        </span>
      </summary>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => void onFetchAuthMe()}
          disabled={loadingAuthMe}
          className="inline-flex items-center gap-2 rounded-lg bg-app-accent px-3 py-2 text-sm font-semibold text-black transition hover:bg-app-accentSoft disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loadingAuthMe ? <span className="spinner" aria-hidden="true" /> : null}
          Call /auth/me
        </button>
        <button
          type="button"
          onClick={() => void onRefreshWorkspace()}
          disabled={loadingWorkspace}
          className="inline-flex items-center gap-2 rounded-lg border border-app-accent/60 bg-app-elevated px-3 py-2 text-sm text-app-text transition hover:border-app-accent hover:text-app-accent disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loadingWorkspace ? <span className="spinner" aria-hidden="true" /> : null}
          Refresh /workspaces/me
        </button>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div>
          <p className="mb-1 text-xs uppercase tracking-[0.14em] text-app-muted">/auth/me</p>
          <pre className="max-h-72 overflow-auto rounded-lg border border-app-border bg-[#0f0f14] p-3 text-xs text-app-muted">
            {authMeJson}
          </pre>
        </div>
        <div>
          <p className="mb-1 text-xs uppercase tracking-[0.14em] text-app-muted">/workspaces/me</p>
          <pre className="max-h-72 overflow-auto rounded-lg border border-app-border bg-[#0f0f14] p-3 text-xs text-app-muted">
            {workspaceJson}
          </pre>
        </div>
      </div>
    </details>
  );
}
