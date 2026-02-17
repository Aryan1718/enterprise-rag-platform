import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/layout/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import ChatPage from "./pages/ChatPage";
import Login from "./pages/Login";
import ObservabilityPage from "./pages/ObservabilityPage";
import Signup from "./pages/Signup";
import UploadPage from "./pages/UploadPage";
import WorkspaceGate from "./pages/WorkspaceGate";
import WorkspaceInfoPage from "./pages/WorkspaceInfoPage";

function RootRedirect() {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-white">
        <div className="inline-flex items-center gap-2 rounded-xl border border-app-border bg-app-surface px-4 py-3 text-sm text-app-muted">
          <span className="spinner" aria-hidden="true" />
          Loading...
        </div>
      </main>
    );
  }

  return <Navigate to={session ? "/workspace" : "/login"} replace />;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route
        path="/workspace"
        element={(
          <ProtectedRoute>
            <WorkspaceGate />
          </ProtectedRoute>
        )}
      />

      <Route
        path="/app"
        element={(
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        )}
      >
        <Route index element={<Navigate to="upload" replace />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="observability" element={<ObservabilityPage />} />
        <Route path="workspace" element={<WorkspaceInfoPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
