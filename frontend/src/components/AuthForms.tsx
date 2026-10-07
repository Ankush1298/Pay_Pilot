"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthContext";
import { useToast } from "@/components/ToastContext";
import { signupPasskey, loginPasskey } from "@/lib/passkeys";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { user, loading, checkAuth } = useAuth();
  const router = useRouter();
  const { show } = useToast();
  const [displayName, setDisplayName] = useState("");
  const [limit, setLimit] = useState("1500");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (user && !loading) router.replace("/dashboard"); }, [user, loading, router]);

  const supported = typeof window === "undefined" || !!window.PublicKeyCredential;

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const ceiling = Math.max(0, Math.min(25000, Number(limit) || 1500));
      await signupPasskey(displayName || "PayPilot user", { per_tx_limit: ceiling, daily_limit: Math.min(25000, Math.max(ceiling * 3, 5000)) });
      await checkAuth();
      show("ok", "Account created with your passkey.");
    } catch (err: any) { show("crit", err.message || "Sign up failed"); }
    finally { setBusy(false); }
  };

  const handleLogin = async () => {
    setBusy(true);
    try {
      const result = await loginPasskey();
      await checkAuth();
      show(result?.new_device ? "warn" : "ok", result?.new_device ? "Signed in. This device is pending; payments stay locked until it is trusted." : "Welcome back.");
    } catch (err: any) { show("crit", err.message || "Login failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="auth-wrap">
      <div className="card card-glass auth-card">
        <div className="text-center" style={{ marginBottom: "1.5rem" }}>
          <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
          <p>{mode === "login" ? "Sign in with your passkey. No password to remember." : "Passkey-only: no password, no seed phrase."}</p>
        </div>
        {!supported && <div className="alert-strip alert-strip-warn" role="alert">This browser does not support passkeys. Try a current Chrome, Safari, Edge or Firefox.</div>}
        {mode === "login" ? (
          <div className="flex-col gap-4">
            <button onClick={handleLogin} className="btn btn-primary btn-full btn-lg" disabled={busy}>{busy ? <span className="spinner" /> : "Log in with passkey"}</button>
            <p className="text-center">New here? <Link href="/register" className="text-accent">Create an account</Link></p>
          </div>
        ) : (
          <form onSubmit={handleSignup} className="flex-col gap-4">
            <div className="field">
              <label htmlFor="displayName">Display name</label>
              <input id="displayName" type="text" className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Your name" maxLength={40} autoComplete="nickname" />
            </div>
            <div className="field">
              <label htmlFor="ceiling">Automatic approval ceiling (₹)</label>
              <input id="ceiling" type="number" min="0" max="25000" className="input" value={limit} onChange={(e) => setLimit(e.target.value)} required />
              <span className="field-help">Payments above this always need your passkey. The AI never sees this rule.</span>
            </div>
            <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={busy}>{busy ? <span className="spinner" /> : "Create account with passkey"}</button>
            <p className="text-center">Already registered? <Link href="/login" className="text-accent">Log in</Link></p>
          </form>
        )}
        <p className="auth-fine">Your fingerprint or face never leaves your device. See <Link href="/security">how it works</Link>.</p>
      </div>
    </div>
  );
}
