import { SendHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import CitationsBar, { type CitationChip } from "./CitationsBar";

import { useAuth } from "../../context/AuthContext";
import {
  apiGetQuery,
  apiListQueries,
  apiQueryStream,
  ApiError,
  type DocumentRecord,
  type QueryCitation,
  type QueryHistoryItem,
  type UsageToday,
} from "../../lib/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations: CitationChip[];
  failed?: boolean;
};

type ChatPanelProps = {
  document: DocumentRecord | null;
  onCitationClick: (citation: CitationChip) => void;
  loadingCitationChunkId: string | null;
  onUsageUpdate: (usage: UsageToday) => void;
  onStreamError: (message: string) => void;
};

function normalizeCitations(citations: QueryCitation[]): CitationChip[] {
  return citations.map((item) => ({
    chunk_id: item.chunk_id,
    page_number: item.page_number,
    document_id: item.document_id,
  }));
}

export default function ChatPanel({
  document,
  onCitationClick,
  loadingCitationChunkId,
  onUsageUpdate,
  onStreamError,
}: ChatPanelProps) {
  const { accessToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const activeControllerRef = useRef<AbortController | null>(null);
  const activeStreamIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!accessToken || !document) {
      setHistory([]);
      return;
    }
    let active = true;
    const loadHistory = async () => {
      setLoadingHistory(true);
      try {
        const response = await apiListQueries(accessToken, { document_id: document.id, limit: 10, offset: 0 });
        if (active) {
          setHistory(response.items);
        }
      } catch {
        if (active) {
          setHistory([]);
        }
      } finally {
        if (active) {
          setLoadingHistory(false);
        }
      }
    };
    void loadHistory();
    return () => {
      active = false;
    };
  }, [accessToken, document]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || !accessToken || !document) {
      return;
    }

    activeControllerRef.current?.abort();

    const userMessage: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      text: trimmed,
      citations: [],
    };
    const assistantMessageId = `a-${Date.now()}`;
    const controller = new AbortController();
    activeControllerRef.current = controller;
    activeStreamIdRef.current = assistantMessageId;

    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantMessageId, role: "assistant", text: "", citations: [], failed: false },
    ]);
    setInput("");
    let streamReportedError = false;

    try {
      await apiQueryStream(
        accessToken,
        {
          document_id: document.id,
          question: trimmed,
        },
        {
          onDelta: (delta) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantMessageId ? { ...message, text: `${message.text}${delta}` } : message,
              ),
            );
          },
          onCitations: (citations) => {
            const chips = normalizeCitations(citations);
            setMessages((current) =>
              current.map((message) => (message.id === assistantMessageId ? { ...message, citations: chips } : message)),
            );
          },
          onUsage: (usage) => {
            onUsageUpdate(usage);
          },
          onError: (message) => {
            streamReportedError = true;
            onStreamError(message);
          },
        },
        controller.signal,
      );
      try {
        const refreshed = await apiListQueries(accessToken, { document_id: document.id, limit: 10, offset: 0 });
        setHistory(refreshed.items);
      } catch {
        // Ignore history refresh failures after a successful query response.
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      const message = error instanceof ApiError ? error.message : "Query failed. Please try again.";
      if (!streamReportedError) {
        onStreamError(message);
      }
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId
            ? {
                ...item,
                failed: true,
                text: item.text ? `${item.text}\n\n[Stream failed] ${message}` : `[Stream failed] ${message}`,
              }
            : item,
        ),
      );
    } finally {
      if (activeStreamIdRef.current === assistantMessageId) {
        activeStreamIdRef.current = null;
        activeControllerRef.current = null;
      }
    }
  };

  useEffect(() => {
    if (!document) {
      return;
    }
    activeControllerRef.current?.abort();
    activeControllerRef.current = null;
    activeStreamIdRef.current = null;
    setMessages([]);
  }, [document?.id]);

  const loadHistoryItem = async (queryId: string) => {
    if (!accessToken) {
      return;
    }
    try {
      const detail = await apiGetQuery(accessToken, queryId);
      const defaultDocumentId =
        detail.document_ids.length > 0 ? String(detail.document_ids[0]) : document?.id ?? "";
      const citations: CitationChip[] = detail.citations.map((item) => ({
        chunk_id: item.chunk_id,
        page_number: item.page_number,
        document_id: defaultDocumentId,
      }));
      setMessages([
        { id: `h-q-${detail.id}`, role: "user", text: detail.question, citations: [] },
        {
          id: `h-a-${detail.id}`,
          role: "assistant",
          text: detail.answer ?? detail.error_message ?? "",
          citations,
        },
      ]);
    } catch {
      // Keep current chat state if a history item fails to load.
    }
  };

  useEffect(() => {
    return () => {
      activeControllerRef.current?.abort();
      activeControllerRef.current = null;
      activeStreamIdRef.current = null;
    };
  }, []);

  if (!document) {
    return (
      <section className="flex h-full min-h-[70vh] items-center justify-center rounded-2xl border border-app-border bg-white p-6 text-center">
        <div>
          <p className="text-lg font-semibold text-app-text">Select a document from the left to start chatting.</p>
          <p className="mt-2 text-sm text-app-muted">Only indexed documents can be queried.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="grid min-h-[72vh] grid-cols-1 gap-4 lg:grid-cols-[1fr_300px]">
      <div className="flex min-h-[72vh] flex-col rounded-2xl border border-app-border bg-white">
        <header className="border-b border-app-border px-5 py-4">
          <p className="text-xs uppercase tracking-[0.08em] text-app-muted">Document Chat</p>
          <h2 className="mt-1 text-lg font-semibold text-app-text">{document.filename}</h2>
          <p className="mt-1 text-sm text-app-muted">Status: {document.status === "indexed" ? "Indexed" : document.status}</p>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto bg-app-surface px-5 py-4">
          {messages.length === 0 ? (
            <p className="text-sm text-app-muted">Ask a question about this document to start the conversation.</p>
          ) : (
            messages.map((message) => (
              <article
                key={message.id}
                className={`max-w-[85%] rounded-2xl border px-3 py-2 text-sm ${
                  message.role === "user"
                    ? "ml-auto border-app-accent bg-app-accentSoft text-app-text"
                    : message.failed
                      ? "border-app-danger/70 bg-red-50 text-app-text"
                      : "border-app-border bg-white text-app-text"
                }`}
              >
                <p className="whitespace-pre-wrap">{message.text}</p>
                {message.role === "assistant" ? (
                  <CitationsBar
                    citations={message.citations}
                    loadingChunkId={loadingCitationChunkId}
                    onClickCitation={onCitationClick}
                  />
                ) : null}
              </article>
            ))
          )}
        </div>

        <div className="border-t border-app-border p-4">
          <div className="flex items-end gap-2">
            <textarea
              className="app-input min-h-[48px] resize-none"
              rows={2}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask a question about this document"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
            />

            <button type="button" className="btn-primary h-[46px] w-[46px] flex-none p-0" onClick={() => void sendMessage()}>
              <SendHorizontal size={16} />
            </button>
          </div>
        </div>
      </div>
      <aside className="rounded-2xl border border-app-border bg-white p-4">
        <p className="text-xs uppercase tracking-[0.08em] text-app-muted">Recent Questions</p>
        {loadingHistory ? <p className="mt-3 text-sm text-app-muted">Loading...</p> : null}
        {!loadingHistory && history.length === 0 ? <p className="mt-3 text-sm text-app-muted">No recent questions.</p> : null}
        <div className="mt-3 space-y-2">
          {history.map((item) => (
            <button
              key={item.id}
              type="button"
              className="w-full rounded-lg border border-app-border bg-app-surface px-3 py-2 text-left hover:border-app-accent"
              onClick={() => {
                void loadHistoryItem(item.id);
              }}
            >
              <p className="truncate text-sm font-medium text-app-text">{item.question}</p>
              <p className="mt-1 truncate text-xs text-app-muted">{item.answer_preview}</p>
            </button>
          ))}
        </div>
      </aside>
    </section>
  );
}
