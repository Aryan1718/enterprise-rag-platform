import { useEffect, useMemo, useState } from "react";

import UploadPanel from "../components/upload/UploadPanel";
import { useAuth } from "../context/AuthContext";
import { useAppShellContext } from "../components/layout/AppShell";
import { apiDeleteDocument } from "../lib/api";

const processingStatuses = new Set(["pending_upload", "uploaded", "queued", "extracting", "indexing"]);

function statusBadge(status: string): string {
  if (status === "indexed" || status === "ready") {
    return "border-app-success/30 bg-green-50 text-green-700";
  }
  if (status === "failed") {
    return "border-app-danger/30 bg-red-50 text-red-700";
  }
  return "border-amber-200 bg-amber-50 text-amber-700";
}

function statusLabel(status: string): string {
  if (status === "indexed" || status === "ready") {
    return "Indexed";
  }

  if (status === "pending_upload") {
    return "Pending upload";
  }

  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function UploadPage() {
  const { accessToken } = useAuth();
  const { documents, loading, refreshDocuments, activeDocument, setActiveDocumentId } = useAppShellContext();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const hasProcessing = useMemo(
    () => documents.some((doc) => processingStatuses.has(doc.status)),
    [documents],
  );

  useEffect(() => {
    if (!hasProcessing) {
      return;
    }

    const interval = window.setInterval(() => {
      void refreshDocuments();
    }, 4000);

    return () => {
      window.clearInterval(interval);
    };
  }, [hasProcessing, refreshDocuments]);

  if (!accessToken) {
    return null;
  }

  const handleDelete = async (documentId: string, filename: string) => {
    const confirmed = window.confirm(`Delete document "${filename}"? This cannot be undone.`);
    if (!confirmed) {
      return;
    }

    try {
      setDeletingId(documentId);
      await apiDeleteDocument(accessToken, documentId);
      if (activeDocument?.id === documentId) {
        setActiveDocumentId(null);
      }
      await refreshDocuments();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Delete failed";
      window.alert(message);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-5 p-4 md:p-6">
      <UploadPanel token={accessToken} onAfterUpload={refreshDocuments} documents={documents} />

      <section className="rounded-2xl border border-app-border bg-white">
        <div className="border-b border-app-border px-5 py-4">
          <h2 className="text-lg font-semibold text-app-text">Documents</h2>
          <p className="mt-1 text-sm text-app-muted">Ingestion status updates automatically while processing is active.</p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-app-border text-sm">
            <thead className="bg-app-surface text-left text-xs uppercase tracking-[0.08em] text-app-muted">
              <tr>
                <th className="px-5 py-3 font-medium">Filename</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Pages</th>
                <th className="px-5 py-3 font-medium">Updated</th>
                <th className="px-5 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-app-border bg-white">
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td className="px-5 py-3 text-app-text">{doc.filename}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadge(doc.status)}`}>
                      {statusLabel(doc.status)}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-app-muted">{doc.page_count ?? "--"}</td>
                  <td className="px-5 py-3 text-app-muted">{doc.updated_at ? new Date(doc.updated_at).toLocaleString() : "--"}</td>
                  <td className="px-5 py-3 text-right">
                    <button
                      type="button"
                      className="inline-flex items-center rounded-lg border border-red-200 bg-white px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                      onClick={() => void handleDelete(doc.id, doc.filename)}
                      disabled={deletingId === doc.id}
                    >
                      {deletingId === doc.id ? "Deleting..." : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}

              {!loading && documents.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-app-muted">
                    No documents yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
