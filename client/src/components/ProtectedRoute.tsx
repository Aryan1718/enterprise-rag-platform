import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-app-bg px-4">
        <div className="inline-flex items-center gap-2 rounded-xl border border-app-border bg-app-surface px-4 py-3 text-sm text-app-muted">
          <span className="spinner" aria-hidden="true" />
          Restoring session...
        </div>
      </main>
    );
  }

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
