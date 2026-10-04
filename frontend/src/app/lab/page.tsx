"use client";

import { useState } from "react";
import { useAuth } from "@/components/AuthContext";
import { useToast } from "@/components/ToastContext";
import { api } from "@/lib/api";

const SCENARIOS = [
  { id: "auto_approve", title: "Auto Approval", desc: "Safe, low-cost booking on a trusted device." },
  { id: "step_up", title: "Step-Up Verification", desc: "High-value transaction triggers passkey request." },
  { id: "compromised_ai", title: "Compromised AI", desc: "AI is tricked into paying an attacker. Policy blocks it." },
  { id: "new_device", title: "New Device Lockout", desc: "Attempted transaction from an untrusted device." },
  { id: "lookalike", title: "Lookalike Domain", desc: "Agent tries to book on a fake imitating domain." },
  { id: "daily_limit", title: "Daily Limit Exceeded", desc: "Successive bookings breach the 24h limit." },
  { id: "velocity", title: "Velocity Check", desc: "Too many rapid, small transactions." },
];

export default function LabPage() {
  const { user } = useAuth();
  const { show } = useToast();
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  if (!user) return null;

  const runScenario = async (id: string) => {
    setRunning(id);
    setResult(null);
    try {
      const res = await api.lab.run(id);
      setResult(res);
      show("ok", "Scenario completed");
    } catch (err: any) {
      show("crit", err.message || "Failed to run scenario");
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Security Lab</h1>
        <p>Run isolated attack scenarios against a lab session. Lab strikes do not affect your real account or wallet.</p>
      </div>

      <div className="grid-2">
        <div className="flex-col gap-3">
          {SCENARIOS.map(s => (
            <div key={s.id} className={`card option-card ${running === s.id ? "glow-border" : ""}`} onClick={() => !running && runScenario(s.id)}>
              <div className="flex justify-between items-start">
                <div>
                  <h4>{s.title}</h4>
                  <div className="text-sm text-secondary" style={{ marginTop: "4px" }}>{s.desc}</div>
                </div>
                {running === s.id && <div className="spinner"></div>}
              </div>
            </div>
          ))}
        </div>

        <div>
          {result ? (
            <div className="card flex-col gap-4 animate-fade-in" style={{ position: "sticky", top: "80px" }}>
              <div>
                <h3 className="text-accent">{result.title}</h3>
                <p style={{ marginTop: "6px" }}>{result.story}</p>
              </div>
              <div className="divider" />
              
              <div className="flex-col gap-3">
                {result.steps.map((step: any, idx: number) => (
                  <div key={idx} className="stat-box" style={{ background: "var(--bg-surface)" }}>
                    <div className="flex items-center gap-2" style={{ marginBottom: "0.5rem" }}>
                      <span className={`badge ${step.status === "ok" ? "badge-ok" : step.status === "step_up" ? "badge-warn" : step.status === "blocked" ? "badge-danger" : "badge-info"}`}>
                        {step.status.toUpperCase()}
                      </span>
                      <span className="text-sm font-medium">{step.label}</span>
                    </div>
                    
                    {step.result?.verdict && (
                      <div className="text-sm">
                        <span className="text-muted">Verdict:</span> <span className={`verdict-${step.result.verdict.toLowerCase().replace('_', '')}`} style={{ display: "inline-block", padding: "0.1rem 0.5rem", fontSize: "0.65rem", marginLeft: "6px" }}>{step.result.verdict}</span>
                        {step.result.reasons?.length > 0 && (
                          <ul style={{ marginTop: "0.5rem", paddingLeft: "1.2rem", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                            {step.result.reasons.map((r: any, i: number) => (
                              <li key={i}>{r.message}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    {step.message && (
                      <div className="text-sm text-danger mt-1">{step.message}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="card empty-state h-full">
              <p>Select a scenario from the left to see how the policy engine reacts.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
