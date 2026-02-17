import { File, UploadCloud, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { DragEventHandler } from "react";

import {
  apiUploadComplete,
  apiUploadPrepare,
  apiUploadToSignedUrl,
  type DocumentRecord,
  type DocumentStatus,
} from "../../lib/api";
import { cn } from "../../lib/utils";

const MAX_FILES = 100;
const CONCURRENCY = 4;

type UploadTaskState =
  | "queued"
  | "preparing"
  | "uploading"
  | "completing"
  | "extracting"
  | "indexing"
  | "indexed"
  | "failed";

type UploadTask = {
  id: string;
  file: File;
  state: UploadTaskState;
  progress: number;
  message?: string;
  documentId?: string;
};

type UploadPanelProps = {
  token: string;
  onAfterUpload: () => Promise<void>;
  documents: DocumentRecord[];
};

function statusLabel(status: UploadTaskState): string {
  if (status === "preparing") return "Preparing";
  if (status === "uploading") return "Uploading";
  if (status === "completing") return "Completing";
  if (status === "extracting") return "Extracting";
  if (status === "indexing") return "Indexing";
  if (status === "indexed") return "Indexed";
  if (status === "failed") return "Failed";
  return "Queued";
}

function mapDocumentStatus(status: string): UploadTaskState {
  const docStatus = status.toLowerCase() as DocumentStatus;

  if (docStatus === "indexed" || docStatus === "ready") return "indexed";
  if (docStatus === "extracting") return "extracting";
  if (docStatus === "indexing") return "indexing";
  if (docStatus === "uploaded") return "indexing";
  if (docStatus === "failed") return "failed";
  return "queued";
}

export default function UploadPanel({ token, onAfterUpload, documents }: UploadPanelProps) {
  const [tasks, setTasks] = useState<UploadTask[]>([]);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const startedTaskIdsRef = useRef<Set<string>>(new Set());

  const activeCount = useMemo(
    () => tasks.filter((task) => ["preparing", "uploading", "completing"].includes(task.state)).length,
    [tasks],
  );

  const queuedTasks = useMemo(() => tasks.filter((task) => task.state === "queued"), [tasks]);

  const updateTask = useCallback((id: string, patch: Partial<UploadTask>) => {
    setTasks((current) => current.map((task) => (task.id === id ? { ...task, ...patch } : task)));
  }, []);

  const runTask = useCallback(async (task: UploadTask) => {
    try {
      const contentType = task.file.type || "application/pdf";

      const prepared = await apiUploadPrepare(token, {
        filename: task.file.name,
        content_type: contentType,
        file_size_bytes: task.file.size,
        idempotency_key: task.id,
      });

      updateTask(task.id, { state: "uploading", progress: 35, documentId: prepared.document_id });
      await apiUploadToSignedUrl(prepared.upload_url, task.file);

      updateTask(task.id, { state: "completing", progress: 80 });
      const completed = await apiUploadComplete(token, {
        document_id: prepared.document_id,
        bucket: prepared.bucket,
        storage_path: prepared.storage_path,
      });

      updateTask(task.id, {
        state: mapDocumentStatus(completed.status),
        progress: completed.status === "failed" ? 0 : 100,
      });

      await onAfterUpload();
    } catch (err) {
      updateTask(task.id, {
        state: "failed",
        progress: 0,
        message: err instanceof Error ? err.message : "Upload failed",
      });
    } finally {
      startedTaskIdsRef.current.delete(task.id);
    }
  }, [onAfterUpload, token, updateTask]);

  useEffect(() => {
    if (queuedTasks.length === 0) {
      return;
    }

    const slots = Math.max(CONCURRENCY - activeCount, 0);
    if (slots === 0) {
      return;
    }

    const toStart = queuedTasks
      .filter((task) => !startedTaskIdsRef.current.has(task.id))
      .slice(0, slots);

    toStart.forEach((task) => {
      startedTaskIdsRef.current.add(task.id);
      updateTask(task.id, { state: "preparing", progress: 10 });
      void runTask(task);
    });
  }, [activeCount, queuedTasks, runTask, updateTask]);

  useEffect(() => {
    if (documents.length === 0) {
      return;
    }

    const indexedById = new Set(
      documents
        .filter((doc) => doc.status === "indexed" || doc.status === "ready")
        .map((doc) => doc.id),
    );
    const indexedByFilename = new Set(
      documents
        .filter((doc) => doc.status === "indexed" || doc.status === "ready")
        .map((doc) => doc.filename),
    );

    setTasks((current) =>
      current.filter((task) => {
        if (task.documentId && indexedById.has(task.documentId)) {
          return false;
        }
        if (!task.documentId && indexedByFilename.has(task.file.name)) {
          return false;
        }
        return true;
      }),
    );
  }, [documents]);

  const addFiles = (incoming: FileList | File[]) => {
    const files = Array.from(incoming).filter((file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"));

    if (files.length === 0) {
      setError("Select at least one PDF file.");
      return;
    }

    setError(null);

    setTasks((current) => {
      if (current.length + files.length > MAX_FILES) {
        setError(`You can upload up to ${MAX_FILES} files at once.`);
        return current;
      }

      const additions: UploadTask[] = files.map((file, idx) => ({
        id: `${file.name}-${file.size}-${Date.now()}-${idx}`,
        file,
        state: "queued",
        progress: 0,
      }));

      return [...current, ...additions];
    });
  };

  const onDrop: DragEventHandler<HTMLLabelElement> = (event) => {
    event.preventDefault();
    addFiles(event.dataTransfer.files);
  };

  return (
    <section className="rounded-2xl border border-app-border bg-white p-5 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-app-text">Upload documents</h2>
          <p className="mt-1 text-sm text-app-muted">Drop PDFs or browse to upload. Maximum 100 files.</p>
        </div>
        <button
          type="button"
          className="btn-secondary gap-1.5"
          onClick={() => inputRef.current?.click()}
        >
          <UploadCloud size={15} />
          Browse files
        </button>
      </div>

      <label
        onDragOver={(event) => event.preventDefault()}
        onDrop={onDrop}
        className="mt-5 flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-app-border bg-app-surface px-5 py-10 text-center hover:border-app-accent"
      >
        <UploadCloud className="text-app-accent" size={28} />
        <p className="mt-3 text-sm font-medium text-app-text">Drag and drop PDFs here</p>
        <p className="mt-1 text-xs text-app-muted">or click Browse files</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={(event) => {
            if (event.target.files) {
              addFiles(event.target.files);
              event.target.value = "";
            }
          }}
        />
      </label>

      {error ? <p className="mt-3 text-sm text-app-danger">{error}</p> : null}

      <div className="mt-5 space-y-2">
        {tasks.map((task) => (
          <article key={task.id} className="rounded-xl border border-app-border bg-app-surface p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-app-text">
                  <File size={14} className="mr-1 inline text-app-muted" />
                  {task.file.name}
                </p>
                <p className="mt-1 text-xs text-app-muted">{statusLabel(task.state)}</p>
              </div>

              {task.state === "failed" ? (
                <button
                  type="button"
                  className="rounded-md border border-app-border bg-white p-1 text-app-muted hover:border-app-accent"
                  onClick={() => setTasks((current) => current.filter((entry) => entry.id !== task.id))}
                >
                  <X size={14} />
                </button>
              ) : null}
            </div>

            <div className="mt-2 h-2 rounded-full bg-white">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  task.state === "failed" ? "bg-app-danger" : "bg-app-accent",
                )}
                style={{ width: `${task.progress}%` }}
              />
            </div>

            {task.message ? <p className="mt-1 text-xs text-app-danger">{task.message}</p> : null}
          </article>
        ))}

        {tasks.length === 0 ? <p className="text-sm text-app-muted">No files queued yet.</p> : null}
      </div>
    </section>
  );
}
