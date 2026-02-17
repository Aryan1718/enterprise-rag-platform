import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const { session, signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const validEmail = useMemo(() => emailPattern.test(email.trim()), [email]);

  if (session) {
    return <Navigate to="/workspace" replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedEmail = email.trim();

    if (!emailPattern.test(trimmedEmail)) {
      setError("Enter a valid email address.");
      return;
    }

    if (!password) {
      setError("Password is required.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      await signIn(trimmedEmail, password);
      navigate("/workspace", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-white px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-app-border bg-white p-8 shadow-card">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-app-muted">Enterprise RAG</p>
        <h1 className="mt-3 text-3xl font-semibold text-app-text">Sign in</h1>
        <p className="mt-2 text-sm text-app-muted">Access your workspace and document assistant.</p>

        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-app-text">
              Email
            </label>
            <input
              id="email"
              type="email"
              className="app-input"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
              autoComplete="email"
              required
            />
            {!validEmail && email.length > 0 ? <p className="mt-1 text-xs text-app-danger">Invalid email format.</p> : null}
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-app-text">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="app-input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error ? <p className="text-sm text-app-danger">{error}</p> : null}

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-sm text-app-muted">
          Need an account?{" "}
          <Link to="/signup" className="font-semibold text-app-accent hover:text-app-accentDark">
            Sign up
          </Link>
        </p>
      </section>
    </main>
  );
}
