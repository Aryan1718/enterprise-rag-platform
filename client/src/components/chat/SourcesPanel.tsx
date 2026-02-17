import { X } from "lucide-react";

import type { CitationSource } from "../../lib/api";

type SourcesPanelProps = {
  open: boolean;
  loading: boolean;
  error: string | null;
  source: CitationSource | null;
  documentName: string | null;
  onClose: () => void;
};

export default function SourcesPanel({ open, loading, error, source, documentName, onClose }: SourcesPanelProps) {
  if (!open) {
    return null;
  }

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-black/25 lg:bg-transparent"
        aria-label="Close sources panel"
        onClick={onClose}
      />
      <aside className="fixed inset-x-0 bottom-0 z-50 h-[75vh] rounded-t-2xl border-t border-app-border bg-white lg:inset-y-0 lg:right-0 lg:left-auto lg:h-full lg:w-[460px] lg:rounded-none lg:border-t-0 lg:border-l">
        <header className="flex items-center justify-between border-b border-app-border px-4 py-3">
          <div>
            <p className="text-xs uppercase tracking-[0.08em] text-app-muted">Sources</p>
            <p className="mt-1 text-sm font-semibold text-app-text">{documentName ?? "Document source"}</p>
          </div>
          <button
            type="button"
            className="rounded-lg border border-app-border bg-white p-1.5 text-app-muted hover:border-app-accent hover:text-app-text"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </header>

        <div className="h-[calc(100%-57px)] overflow-y-auto px-4 py-4">
          {loading ? <p className="text-sm text-app-muted">Loading source...</p> : null}
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          {!loading && !error && source ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-app-border bg-app-surface px-3 py-2">
                <p className="text-xs text-app-muted">Page</p>
                <p className="text-sm font-semibold text-app-text">{source.page_number}</p>
              </div>

              <section>
                <p className="mb-2 text-xs uppercase tracking-[0.08em] text-app-muted">Chunk Text</p>
                <pre className="max-h-[42vh] overflow-auto whitespace-pre-wrap rounded-xl border border-app-border bg-app-surface p-3 text-sm leading-6 text-app-text">
                  {source.chunk_text}
                </pre>
              </section>

              <details className="rounded-xl border border-app-border bg-white p-3">
                <summary className="cursor-pointer text-sm font-medium text-app-text">Full Page Text</summary>
                <pre className="mt-3 max-h-[30vh] overflow-auto whitespace-pre-wrap rounded-lg border border-app-border bg-app-surface p-3 text-sm leading-6 text-app-text">
                  {source.page_text ?? "No page text available."}
                </pre>
              </details>
            </div>
          ) : null}
        </div>
      </aside>
    </>
  );
}
