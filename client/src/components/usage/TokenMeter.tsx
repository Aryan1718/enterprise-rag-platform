import type { UsageTodayResponse } from "../../types/api";

type TokenMeterProps = {
  usage: UsageTodayResponse | null;
  loading?: boolean;
  error?: string | null;
};

export default function TokenMeter({ usage, loading = false, error = null }: TokenMeterProps) {
  if (loading) {
    return <section>Loading usage...</section>;
  }

  if (error) {
    return <section>Usage error: {error}</section>;
  }

  if (!usage) {
    return <section>No usage data yet.</section>;
  }

  const consumed = usage.used + usage.reserved;
  const percent = usage.limit > 0 ? Math.min(100, Math.round((consumed / usage.limit) * 100)) : 0;

  return (
    <section>
      <h3>Today&apos;s Token Budget</h3>
      <p>
        Used: <strong>{usage.used}</strong>
      </p>
      <p>
        Reserved: <strong>{usage.reserved}</strong>
      </p>
      <p>
        Remaining: <strong>{usage.remaining}</strong> / {usage.limit}
      </p>
      <p>Consumed: {percent}%</p>
      <p>Resets At (UTC): {new Date(usage.resets_at).toUTCString()}</p>
    </section>
  );
}
