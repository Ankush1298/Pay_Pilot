"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthContext";
import { useToast } from "@/components/ToastContext";
import { api } from "@/lib/api";
import { signupPasskey, loginPasskey } from "@/lib/passkeys";

export default function AuthPage() {
  const { user, loading, checkAuth } = useAuth();
  const router = useRouter();
  const { show } = useToast();
  
  const [isLogin, setIsLogin] = useState(true);
  const [displayName, setDisplayName] = useState("");
  const [limit, setLimit] = useState("1500");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user && !loading) {
      router.push("/dashboard");
    }
  }, [user, loading, router]);

  if (loading || user) {
    return (
      <div className="flex items-center justify-center" style={{ height: "100vh" }}>
        <div className="spinner"></div>
      </div>
    );
  }

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const ceiling = Math.max(0, Math.min(25000, Number(limit) || 1500));
      await signupPasskey(displayName || "IntentLock user", { per_tx_limit: ceiling, daily_limit: Math.max(ceiling * 3, 5000) });
      await checkAuth();
      show("ok", "Account created successfully with Passkey.");
    } catch (err: any) {
      show("crit", err.message || "Sign up failed");
    } finally {
      setBusy(false);
    }
  };

  const handleLogin = async () => {
    setBusy(true);
    try {
      const result = await loginPasskey();
      await checkAuth();
      show(result?.new_device ? "warn" : "ok", result?.new_device ? "Signed in. This device is pending; payments stay locked until it is trusted." : "Welcome back.");
    } catch (err: any) {
      show("crit", err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center justify-center" style={{ minHeight: "100vh", padding: "2rem" }}>
      <div className="card card-glass animate-fade-up" style={{ width: "100%", maxWidth: "400px" }}>
        <div className="text-center" style={{ marginBottom: "2rem" }}>
          <h1 style={{ marginBottom: "0.5rem" }}>IntentLock</h1>
          <p>Passkey-only authorization for AI actions</p>
        </div>
        
        {isLogin ? (
          <div className="flex-col gap-4">
            <button onClick={handleLogin} className="btn btn-primary btn-full" disabled={busy}>
              {busy ? <div className="spinner"></div> : "Log in with Passkey"}
            </button>
            <div className="text-center" style={{ marginTop: "1.5rem" }}>
              <p>
                Don't have an account?{" "}
                <a href="#" onClick={(e) => { e.preventDefault(); setIsLogin(false); }} className="text-accent">
                  Sign up
                </a>
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSignup} className="flex-col gap-4">
            <div className="field">
              <label>Display name</label>
              <input
                type="text"
                className="input"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="Your name"
                maxLength={40}
              />
            </div>
            <div className="field">
              <label>Automatic approval ceiling (₹)</label>
              <input type="number" min="0" max="25000" className="input" value={limit} onChange={e => setLimit(e.target.value)} required />
              <span className="field-help">Used by the policy engine. The AI never receives this rule.</span>
            </div>
            
            <button type="submit" className="btn btn-primary btn-full" disabled={busy} style={{ marginTop: "0.5rem" }}>
              {busy ? <div className="spinner"></div> : "Sign up with Passkey"}
            </button>
            
            <div className="text-center" style={{ marginTop: "1.5rem" }}>
              <p>
                Already have an account?{" "}
                <a href="#" onClick={(e) => { e.preventDefault(); setIsLogin(true); }} className="text-accent">
                  Sign In
                </a>
              </p>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
