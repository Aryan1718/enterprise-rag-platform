type StatsCardProps = {
  label: string;
  value: string;
  helper?: string;
};

export default function StatsCard({ label, value, helper }: StatsCardProps) {
  return (
    <article className="rounded-xl border border-app-border bg-app-surface p-4 shadow-card">
      <p className="text-xs uppercase tracking-[0.14em] text-app-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-app-text">{value}</p>
      {helper ? <p className="mt-1 text-xs text-app-muted">{helper}</p> : null}
    </article>
  );
}
