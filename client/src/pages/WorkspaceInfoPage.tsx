import { useMemo } from "react";

import { useAppShellContext } from "../components/layout/AppShell";

function statusCount(source: Record<string, number>, keys: string[]): number {
  return keys.reduce((sum, key) => sum + Number(source[key] ?? 0), 0);
}

export default function WorkspaceInfoPage() {
  const { workspace, refreshWorkspace } = useAppShellContext();

  const usage = workspace?.usage_today;

  const progress = useMemo(() => {
    if (!usage || usage.limit <= 0) {
      return 0;
    }

    return Math.min(((usage.used + usage.reserved) / usage.limit) * 100, 100);
  }, [usage]);

  const docsByStatus = workspace?.documents_by_status ?? {};

  return (
    <div className="space-y-5 p-4 md:p-6">
      <section className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-app-text">Workspace Info</h2>
            <p className="mt-1 text-sm text-app-muted">Metadata and daily token usage.</p>
          </div>
          <button type="button" className="btn-secondary" onClick={() => void refreshWorkspace()}>
            Refresh
          </button>
        </div>

        <dl className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-app-border bg-app-surface p-4">
            <dt className="text-xs uppercase tracking-[0.08em] text-app-muted">Workspace name</dt>
            <dd className="mt-2 text-sm font-semibold text-app-text">{workspace?.name ?? "--"}</dd>
          </div>
          <div className="rounded-xl border border-app-border bg-app-surface p-4">
            <dt className="text-xs uppercase tracking-[0.08em] text-app-muted">Workspace ID</dt>
            <dd className="mt-2 break-all text-sm text-app-text">{workspace?.id ?? "--"}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
        <h3 className="text-base font-semibold text-app-text">Daily usage</h3>

        <div className="mt-4 h-3 rounded-full bg-app-surface">
          <div className="h-full rounded-full bg-app-accent" style={{ width: `${progress}%` }} />
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Metric label="Used" value={usage ? usage.used.toLocaleString() : "--"} />
          <Metric label="Reserved" value={usage ? usage.reserved.toLocaleString() : "--"} />
          <Metric label="Remaining" value={usage ? usage.remaining.toLocaleString() : "--"} />
          <Metric label="Limit" value={usage ? usage.limit.toLocaleString() : "--"} />
          <Metric label="Resets at" value={usage?.resets_at ? new Date(usage.resets_at).toLocaleString() : "--"} />
        </div>
      </section>

      <section className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
        <h3 className="text-base font-semibold text-app-text">Documents by status</h3>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Metric label="Ready" value={statusCount(docsByStatus, ["indexed", "ready"]).toString()} />
          <Metric label="Processing" value={statusCount(docsByStatus, ["pending_upload", "uploaded", "queued", "extracting", "indexing"]).toString()} />
          <Metric label="Failed" value={statusCount(docsByStatus, ["failed"]).toString()} />
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-app-border bg-app-surface p-4">
      <p className="text-xs uppercase tracking-[0.08em] text-app-muted">{label}</p>
      <p className="mt-2 text-sm font-semibold text-app-text">{value}</p>
    </div>
  );
}
