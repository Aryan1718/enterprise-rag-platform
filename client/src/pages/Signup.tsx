import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Signup() {
  const { session, signUp } = useAuth();
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

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const result = await signUp(trimmedEmail, password);
      navigate(result.hasSession ? "/workspace" : "/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-white px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-app-border bg-white p-8 shadow-card">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-app-muted">Enterprise RAG</p>
        <h1 className="mt-3 text-3xl font-semibold text-app-text">Create account</h1>
        <p className="mt-2 text-sm text-app-muted">Set up access to your workspace.</p>

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
              autoComplete="new-password"
              placeholder="Minimum 8 characters"
              required
            />
          </div>

          {error ? <p className="text-sm text-app-danger">{error}</p> : null}

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-sm text-app-muted">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-app-accent hover:text-app-accentDark">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
