import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../context/AuthContext";
import { apiGetObservability, type ObservabilityResponse } from "../lib/api";

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export default function ObservabilityPage() {
  const { accessToken } = useAuth();
  const [data, setData] = useState<ObservabilityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) {
      return;
    }
    let active = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiGetObservability(accessToken);
        if (active) {
          setData(response);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load observability");
          setData(null);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [accessToken]);

  const maxVolume = useMemo(() => {
    if (!data || data.query_volume.length === 0) {
      return 1;
    }
    return Math.max(...data.query_volume.map((point) => point.count), 1);
  }, [data]);

  if (loading) {
    return <div className="p-4 md:p-6 text-sm text-app-muted">Loading observability data...</div>;
  }

  if (error || !data) {
    return <div className="p-4 md:p-6 text-sm text-app-danger">Observability error: {error ?? "unknown"}</div>;
  }

  return (
    <div className="space-y-5 p-4 md:p-6">
      <section className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
        <h2 className="text-xl font-semibold text-app-text">Observability</h2>
        <p className="mt-1 text-sm text-app-muted">
          Generated at {new Date(data.generated_at).toLocaleString()} (last {data.window_days} days)
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Total queries" value={data.query_summary.total_queries.toLocaleString()} />
        <Metric label="Queries (24h)" value={data.query_summary.queries_last_24h.toLocaleString()} />
        <Metric label="Errors (24h)" value={data.query_summary.error_count_last_24h.toLocaleString()} />
        <Metric label="Error rate (24h)" value={pct(data.query_summary.error_rate_last_24h)} />
        <Metric label="Avg latency (24h)" value={`${Math.round(data.query_summary.avg_latency_ms_last_24h)} ms`} />
        <Metric label="P95 latency (24h)" value={`${Math.round(data.query_summary.p95_latency_ms_last_24h)} ms`} />
        <Metric label="Tokens used today" value={data.usage_today.used.toLocaleString()} />
        <Metric label="Tokens remaining" value={data.usage_today.remaining.toLocaleString()} />
      </section>

      <section className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
        <h3 className="text-base font-semibold text-app-text">Query volume (last {data.window_days} days)</h3>
        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-7">
          {data.query_volume.map((point) => {
            const bar = Math.max(8, Math.round((point.count / maxVolume) * 100));
            return (
              <div key={point.date} className="rounded-xl border border-app-border bg-app-surface p-3">
                <p className="text-xs text-app-muted">{point.date}</p>
                <div className="mt-2 h-2 rounded-full bg-white">
                  <div className="h-full rounded-full bg-app-accent" style={{ width: `${bar}%` }} />
                </div>
                <p className="mt-2 text-sm font-semibold text-app-text">{point.count} queries</p>
                <p className="text-xs text-app-muted">{point.errors} errors</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
          <h3 className="text-base font-semibold text-app-text">Document pipeline health</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Metric label="Total" value={data.documents.total.toString()} />
            <Metric label="Ready" value={data.documents.ready.toString()} />
            <Metric label="Processing" value={data.documents.processing.toString()} />
            <Metric label="Failed" value={data.documents.failed.toString()} />
          </div>
        </div>

        <div className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
          <h3 className="text-base font-semibold text-app-text">Top queried documents</h3>
          <div className="mt-4 space-y-2">
            {data.top_documents.length === 0 ? (
              <p className="text-sm text-app-muted">No query data yet.</p>
            ) : (
              data.top_documents.map((item) => (
                <div key={item.document_id} className="rounded-xl border border-app-border bg-app-surface p-3">
                  <p className="truncate text-sm font-semibold text-app-text">{item.filename}</p>
                  <p className="mt-1 text-xs text-app-muted">
                    {item.query_count} queries, {item.error_count} errors
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
        <h3 className="text-base font-semibold text-app-text">Recent query errors</h3>
        <div className="mt-4 space-y-2">
          {data.recent_errors.length === 0 ? (
            <p className="text-sm text-app-muted">No recent query errors.</p>
          ) : (
            data.recent_errors.map((item) => (
              <div key={item.query_id} className="rounded-xl border border-app-border bg-app-surface p-3">
                <p className="text-xs text-app-muted">{new Date(item.created_at).toLocaleString()}</p>
                <p className="mt-1 text-sm font-semibold text-app-text">{item.question}</p>
                <p className="mt-1 text-xs text-app-danger">{item.error_message}</p>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-app-border bg-white p-4">
      <p className="text-xs uppercase tracking-[0.08em] text-app-muted">{label}</p>
      <p className="mt-2 text-sm font-semibold text-app-text">{value}</p>
    </div>
  );
}
