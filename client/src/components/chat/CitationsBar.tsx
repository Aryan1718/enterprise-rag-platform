type CitationChip = {
  chunk_id: string;
  page_number: number;
  document_id: string;
};

type CitationsBarProps = {
  citations: CitationChip[];
  loadingChunkId: string | null;
  onClickCitation: (citation: CitationChip) => void;
};

function uniqueByChunk(citations: CitationChip[]): CitationChip[] {
  const seen = new Set<string>();
  const unique: CitationChip[] = [];
  for (const citation of citations) {
    if (seen.has(citation.chunk_id)) {
      continue;
    }
    seen.add(citation.chunk_id);
    unique.push(citation);
  }
  return unique;
}

export type { CitationChip };

export default function CitationsBar({ citations, loadingChunkId, onClickCitation }: CitationsBarProps) {
  const chips = uniqueByChunk(citations);
  if (chips.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {chips.map((citation) => {
        const isLoading = loadingChunkId === citation.chunk_id;
        return (
          <button
            key={citation.chunk_id}
            type="button"
            className="rounded-full border border-app-border bg-app-surface px-3 py-1 text-xs font-medium text-app-text transition hover:border-app-accent disabled:cursor-wait disabled:opacity-70"
            onClick={() => onClickCitation(citation)}
            disabled={isLoading}
          >
            {isLoading ? "Loading..." : `Page ${citation.page_number}`}
          </button>
        );
      })}
    </div>
  );
}
