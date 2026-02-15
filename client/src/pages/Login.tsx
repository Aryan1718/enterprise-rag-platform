import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import Toast, { type ToastState } from "../components/Toast";
import { useAuth } from "../context/AuthContext";
import { appName } from "../styles/theme";

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const { session, signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  const isValidEmail = useMemo(() => emailPattern.test(email.trim()), [email]);

  if (session) {
    return <Navigate to="/home" replace />;
  }

  const showToast = (message: string, type: "success" | "error") => {
    setToast({ id: Date.now(), message, type });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedEmail = email.trim();

    if (!emailPattern.test(trimmedEmail)) {
      setError("Enter a valid email address.");
      showToast("Please provide a valid email.", "error");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      showToast("Password must be at least 8 characters.", "error");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await signIn(trimmedEmail, password);
      showToast("Signed in successfully.", "success");
      navigate("/home", { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sign in failed.";
      setError(message);
      showToast(message, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-app-bg bg-auth-glow px-4 py-10">
      <div className="absolute -left-32 top-16 h-72 w-72 rounded-full bg-app-accent/20 blur-3xl" aria-hidden="true" />
      <div className="absolute -right-20 bottom-12 h-64 w-64 rounded-full bg-app-accent/15 blur-3xl" aria-hidden="true" />

      <section className="relative z-10 w-full max-w-md rounded-2xl border border-app-border bg-app-surface/95 p-6 shadow-glow backdrop-blur">
        <p className="text-xs uppercase tracking-[0.16em] text-app-muted">{appName}</p>
        <h1 className="mt-2 text-3xl font-semibold text-app-text">Welcome Back</h1>
        <p className="mt-2 text-sm text-app-muted">Sign in to manage your workspace and token budget.</p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-app-muted">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={`w-full rounded-lg border bg-app-elevated px-3 py-2.5 text-sm text-app-text outline-none transition placeholder:text-app-muted/70 focus:ring-2 ${
                error && !isValidEmail
                  ? "border-app-danger focus:ring-app-danger/40"
                  : "border-app-border focus:border-app-accent focus:ring-app-accent/40"
              }`}
              autoComplete="email"
              placeholder="you@example.com"
              required
            />
            {!isValidEmail && email.length > 0 ? (
              <p className="mt-1 text-xs text-red-400">Use a valid email format.</p>
            ) : null}
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-app-muted">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className={`w-full rounded-lg border bg-app-elevated px-3 py-2.5 pr-16 text-sm text-app-text outline-none transition placeholder:text-app-muted/70 focus:ring-2 ${
                  error && password.length < 8
                    ? "border-app-danger focus:ring-app-danger/40"
                    : "border-app-border focus:border-app-accent focus:ring-app-accent/40"
                }`}
                autoComplete="current-password"
                placeholder="At least 8 characters"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md border border-app-border px-2 py-1 text-xs text-app-muted hover:border-app-accent hover:text-app-accent"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            <p className="mt-1 text-xs text-app-muted">Minimum length: 8 characters.</p>
          </div>

          {error ? <p className="text-sm text-red-400">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-app-accent px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-app-accentSoft disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <span className="spinner" aria-hidden="true" /> : null}
            {loading ? "Signing In..." : "Sign In"}
          </button>

          <button
            type="button"
            disabled
            className="w-full rounded-lg border border-app-accent/60 bg-app-elevated px-4 py-2.5 text-sm text-app-muted"
          >
            Forgot password (coming soon)
          </button>
        </form>

        <p className="mt-5 text-sm text-app-muted">
          New here? {" "}
          <Link to="/signup" className="font-semibold text-app-accent hover:text-app-accentSoft">
            Create an account
          </Link>
        </p>
      </section>

      <Toast toast={toast} onClose={() => setToast(null)} />
    </main>
  );
}
