type UsageProgressProps = {
  used: number;
  reserved: number;
  remaining: number;
  limit: number;
  resetsAt: string;
  loading?: boolean;
};

export default function UsageProgress({
  used,
  reserved,
  remaining,
  limit,
  resetsAt,
  loading = false,
}: UsageProgressProps) {
  if (loading) {
    return (
      <section className="rounded-xl border border-app-border bg-app-surface p-4 shadow-card">
        <div className="skeleton h-4 w-36 rounded" />
        <div className="mt-4 skeleton h-3 w-full rounded-full" />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="skeleton h-10 rounded-lg" />
          <div className="skeleton h-10 rounded-lg" />
          <div className="skeleton h-10 rounded-lg" />
          <div className="skeleton h-10 rounded-lg" />
        </div>
      </section>
    );
  }

  const consumed = Math.min(limit, used + reserved);
  const percent = limit > 0 ? Math.round((consumed / limit) * 100) : 0;

  return (
    <section className="rounded-xl border border-app-border bg-app-surface p-4 shadow-card">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-app-text">Usage Progress</h3>
        <span className="rounded-full border border-app-accent/60 bg-app-accent/10 px-2 py-1 text-xs text-app-accent">
          {percent}%
        </span>
      </div>

      <div className="mt-4 h-3 overflow-hidden rounded-full bg-app-elevated">
        <div className="h-full bg-app-accent transition-all" style={{ width: `${percent}%` }} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <p className="text-app-muted">Used</p>
        <p className="text-right text-app-text">{used.toLocaleString()}</p>
        <p className="text-app-muted">Reserved</p>
        <p className="text-right text-app-text">{reserved.toLocaleString()}</p>
        <p className="text-app-muted">Remaining</p>
        <p className="text-right text-app-text">{remaining.toLocaleString()}</p>
        <p className="text-app-muted">Limit</p>
        <p className="text-right text-app-text">{limit.toLocaleString()}</p>
      </div>

      <p className="mt-4 text-xs text-app-muted">
        Resets at (UTC): {resetsAt ? new Date(resetsAt).toUTCString() : "N/A"}
      </p>
    </section>
  );
}
