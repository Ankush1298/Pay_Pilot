"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthContext";
import { useToast } from "@/components/ToastContext";
import { api } from "@/lib/api";
import { assertPasskey } from "@/lib/passkeys";

type Msg = { role: "user" | "agent"; content: string; options?: any[]; browsed?: any[] };

const MOMENTS = [
  { id: "auto_approve", n: "01", title: "₹800 hotel auto-approves", desc: "Trusted device + verified merchant + within policy." },
  { id: "step_up", n: "02", title: "₹2,400 requires verification", desc: "Above the automatic ceiling, so passkey approval is required." },
  { id: "compromised_ai", n: "03", title: "Hijacked AI is blocked", desc: "The agent tries to redirect a valid booking to an attacker." },
  { id: "new_device", n: "04", title: "New device is locked", desc: "It can browse, but transactions stay restricted." },
];

function money(v: any) { return `₹${Number(v || 0).toLocaleString("en-IN")}`; }
function dateTime(ts: any) { return ts ? new Date(Number(ts) * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "—"; }

export default function Dashboard() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const { show } = useToast();
  const [state, setState] = useState<any>(null);
  const [messages, setMessages] = useState<Msg[]>([
    { role: "agent", content: "Tell me what you want to book. I can search across available sites, compare price and reviews, and stop at the security gate before money moves." },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [intent, setIntent] = useState<any>(null);
  const [labResult, setLabResult] = useState<any>(null);
  const [labBusy, setLabBusy] = useState<string | null>(null);
  const [manage, setManage] = useState<any>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const loadState = async () => {
    try { setState(await api.state.get()); }
    catch (e: any) { show("crit", e.message || "Could not load security state"); }
  };

  useEffect(() => { if (!loading && !user) router.replace("/"); }, [loading, user, router]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (user) loadState(); }, [user]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, intent]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    const text = input.trim();
    setInput("");
    setMessages(x => [...x, { role: "user", content: text }]);
    setBusy(true);
    try {
      const r = await api.agent.chat(text);
      setMessages(x => [...x, { role: "agent", content: r.text, options: r.options, browsed: r.browsed }]);
    } catch (e: any) { show("crit", e.message || "Agent request failed"); }
    finally { setBusy(false); }
  };

  const book = async (id: string) => {
    setBusy(true);
    setIntent(null);
    try {
      const r = await api.agent.prepare(id);
      if (r.status === "executed" || r.status === "approved") {
        setIntent(null);
        show("ok", `Auto-approved · ${r.booking_id || "booking confirmed"}`);
        await loadState();
      } else if (r.status === "pending_approval" || r.status === "blocked") {
        setIntent(r);
      } else {
        show("warn", r.error ? `Payment failed: ${r.error}` : `Security gate returned ${r.status}`);
      }
    } catch (e: any) { show("crit", e.message || "Failed to prepare booking"); }
    finally { setBusy(false); }
  };

  const approve = async () => {
    if (!intent || busy) return;
    const id = intent.id;
    setBusy(true);
    try {
      let credential: any = null;
      if (intent.decision?.verdict === "STEP_UP") {
        const opts = await api.intents.approvalOpts(id);
        credential = await assertPasskey(opts);
      }
      const r = await api.intents.approve(id, credential);
      setIntent(null);
      if (r.status === "executed") show("ok", `Approved · ${r.booking_id || r.tx_hash || "completed"}`);
      else if (r.status === "blocked") show("warn", "Security re-check blocked this transaction");
      else show("ok", "Request approved");
      await loadState();
    } catch (e: any) {
      // A second click/tab can race the first approval. Treat a consumed intent as stale UI,
      // not as a new security failure, then refresh the authoritative server state.
      if (e.code === "not_pending" || e.code === "no_intent") {
        setIntent(null);
        await loadState();
        show("info", "This approval was already processed. State refreshed.");
      } else {
        show("crit", e.message || "Verification failed");
      }
    } finally { setBusy(false); }
  };

  const reject = async () => {
    if (!intent) return;
    try { await api.intents.reject(intent.id); show("info", "Request rejected"); }
    catch (e: any) { if (e.code !== "not_pending") show("crit", e.message); }
    finally { setIntent(null); await loadState(); }
  };

  const manageBooking = async (action: "cancel" | "modify", booking: any, units?: number) => {
    setBusy(true);
    try {
      const r = await api.agent.manage(booking.id, action, units);
      setManage(null);
      if (r.status === "pending_approval" || r.status === "blocked") setIntent(r);
      else { show("ok", action === "cancel" ? "Cancellation completed" : "Booking updated"); await loadState(); }
    } catch (e: any) { show("crit", e.message || "Booking action failed"); }
    finally { setBusy(false); }
  };

  const runMoment = async (id: string) => {
    setLabBusy(id);
    try { const r = await api.lab.run(id); setLabResult(r); await loadState(); }
    catch (e: any) { show("crit", e.message || "Scenario failed"); }
    finally { setLabBusy(null); }
  };

  const trusted = state?.me?.device?.status === "trusted";
  const pending = state?.pending?.length || 0;
  const bookings = state?.bookings || [];
  const confirmed = bookings.filter((b: any) => b.status === "confirmed").length;
  const cancelled = bookings.filter((b: any) => b.status === "cancelled").length;
  const recentAudit = (state?.audit || []).slice(0, 6);
  const recentTx = (state?.ledger?.txs || []).slice(0, 5);
  const policy = state?.policy;

  if (!user) return null;

  return (
    <div className="page">
      <div className="page-header page-header-wide">
        <div>
          <div className="eyebrow">SECURE AGENT CONSOLE</div>
          <h1>Good to see you, {user.username}</h1>
          <p>The agent can search and prepare. PayPilot decides whether money is allowed to move.</p>
        </div>
        <div className="header-statuses">
          <span className={`badge ${trusted ? "badge-ok" : "badge-warn"}`}>{trusted ? "Trusted device" : "Device pending"}</span>
          <span className="badge badge-info">{state?.ledger?.simulated ? "Simulated ledger" : "Monad testnet"}</span>
          <span className="badge badge-muted">{pending ? `${pending} approval${pending > 1 ? "s" : ""} waiting` : "No approvals waiting"}</span>
        </div>
      </div>

      <section className="hero-strip">
        <div className="hero-step"><span>01</span><div><strong>AI researches</strong><small>Searches sites, prices, reviews and availability.</small></div></div>
        <div className="hero-line" />
        <div className="hero-step"><span>02</span><div><strong>Policy verifies</strong><small>Intent, device, merchant, amount and destination.</small></div></div>
        <div className="hero-line" />
        <div className="hero-step"><span>03</span><div><strong>You approve when needed</strong><small>Passkey protects sensitive transactions.</small></div></div>
      </section>

      <div className="dashboard-grid">
        <aside className="left-rail">
          <section className="card">
            <div className="card-header"><div><div className="card-title">Demo moments</div><div className="card-sub">Run the security story in four clicks.</div></div></div>
            <div className="moment-list">
              {MOMENTS.map(m => (
                <button key={m.id} className="moment" disabled={!!labBusy} onClick={() => runMoment(m.id)}>
                  <span className="moment-number">{m.n}</span>
                  <span><strong>{m.title}</strong><small>{m.desc}</small></span>
                  {labBusy === m.id ? <span className="spinner" /> : <span className="chevron">›</span>}
                </button>
              ))}
            </div>
            {labResult && <div className="lab-result"><div className="lab-result-title">{labResult.title}</div><p>{labResult.story}</p>{labResult.steps?.slice(-3).map((s: any, i: number) => <div className="lab-step" key={i}><span className={`badge ${s.status === "blocked" ? "badge-danger" : s.status === "step_up" ? "badge-warn" : "badge-ok"}`}>{s.status}</span><span>{s.label}</span></div>)}</div>}
          </section>

          <section className="card">
            <div className="card-header"><div><div className="card-title">Security policy</div><div className="card-sub">Enforced outside the AI.</div></div><a className="text-link" href="/settings">Manage</a></div>
            <div className="policy-summary">
              <div><span>Automatic ceiling</span><strong>Configured</strong></div>
              <div><span>24h spend</span><strong>{money(state?.spent_24h)} <em>/ {money(policy?.daily_limit)}</em></strong></div>
              <div><span>Allowed actions</span><strong>{(policy?.allowed_types || []).length}</strong></div>
            </div>
            <div className="policy-note">A low-risk transaction below the ceiling can auto-approve only when the device, merchant, intent and destination also pass.</div>
          </section>
        </aside>

        <section className="card chat-card">
          <div className="chat-head">
            <div><div className="card-title">AI booking assistant</div><div className="card-sub"><span className="status-dot" /> No payment key · cannot approve its own request</div></div>
            <span className="badge badge-info">Agent discovery</span>
          </div>
          <div className="chat-wrap">
            {messages.map((m, i) => (
              <div key={i} className={`chat-bubble ${m.role} animate-fade-up`}>
                <div>{m.content}</div>
                {m.browsed?.length ? <div className="browse-list"><div className="browse-heading">Browsing activity</div>{m.browsed.map((b: any, j: number) => <div className="browse-row" key={j}><span className={`badge ${b.status === "ok" ? "badge-ok" : b.status === "flagged" ? "badge-danger" : "badge-warn"}`}>{b.status}</span><span className="browse-domain">{b.domain}</span><span className="browse-note">{b.note}</span></div>)}</div> : null}
                {m.options?.length ? <div className="option-grid">{m.options.map((o: any) => <div className={`option-card ${o.best ? "best" : ""}`} key={o.id} role="button" tabIndex={0} onClick={() => !busy && book(o.id)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (!busy) book(o.id); } }}>{o.best && <span className="best-badge">BEST MATCH</span>}<div className="option-title">{o.title}</div><div className="option-meta">{o.merchant_name} · {o.city}</div><div className="rating">★ {o.rating ?? "—"} · {(o.reviews || 0).toLocaleString()} reviews</div><div className="option-price">{money(o.total)}</div><div className="option-meta">{o.perks || "Standard terms"}</div><button className="btn btn-secondary btn-sm" style={{ marginTop: 9 }} disabled={busy}>Review & book</button></div>)}</div> : null}
              </div>
            ))}
            {busy && !intent && <div className="chat-bubble agent"><div className="progress-dots"><span/><span/><span/></div></div>}
            <div ref={bottom} />
          </div>
          <form className="chat-form" onSubmit={send}><input className="input" value={input} onChange={e => setInput(e.target.value)} placeholder="Find the cheapest 4-star hotel in Jaipur under ₹5,000" disabled={busy}/><button className="btn btn-primary" disabled={busy || !input.trim()}>Search</button></form>
        </section>

        <aside className="right-rail">
          <section className="card">
            <div className="card-header"><div><div className="card-title">Security gate</div><div className="card-sub">Independent of the AI.</div></div><span className="badge badge-ok">Protected</span></div>
            <div className="security-stack">
              <div className="security-row"><div className="left"><div className="security-icon">D</div><div><strong>Device</strong><span>{state?.me?.device?.name || "Current device"}</span></div></div><span className={`badge ${trusted ? "badge-ok" : "badge-warn"}`}>{state?.me?.device?.status || "unknown"}</span></div>
              <div className="security-row"><div className="left"><div className="security-icon">K</div><div><strong>Passkey</strong><span>Strong approval credential</span></div></div><span className={`badge ${state?.me?.has_passkey ? "badge-ok" : "badge-warn"}`}>{state?.me?.has_passkey ? "ready" : "add"}</span></div>
              <div className="security-row"><div className="left"><div className="security-icon">I</div><div><strong>Intent binding</strong><span>Purpose · merchant · amount</span></div></div><span className="badge badge-ok">on</span></div>
            </div>
          </section>

          <section className="card">
            <div className="card-header"><div><div className="card-title">Wallet</div><div className="card-sub">{state?.ledger?.simulated ? "Simulated ledger (demo funds)" : "Monad testnet"}</div></div>{!state?.ledger?.simulated && state?.ledger?.faucet_url && <button className="btn btn-sm" onClick={() => window.open(state.ledger.faucet_url, "_blank", "noopener,noreferrer")}>Faucet</button>}</div>
            <div className="wallet-balance">{money(state?.ledger?.balance_inr)}</div>
            <div className="mono address">{state?.ledger?.address || "—"}</div>
          </section>

          <section className="card">
            <div className="card-header"><div><div className="card-title">Security alerts</div><div className="card-sub">Recent policy events</div></div><a className="text-link" href="/history">View all</a></div>
            <div className="activity">{(state?.alerts || []).slice(0, 5).map((a: any, i: number) => <div className="activity-row" key={i}><span className={`activity-dot ${a.level}`}/><div><strong>{a.message}</strong><span>{dateTime(a.ts)}</span></div></div>)}{!state?.alerts?.length && <div className="empty-inline">No alerts.</div>}</div>
          </section>
        </aside>
      </div>

      <section className="card section-card">
        <div className="card-header"><div><div className="card-title">Booking history</div><div className="card-sub">Every booking stays visible here, including cancelled bookings.</div></div><div className="history-counts"><span>{confirmed} active</span><span>{cancelled} cancelled</span><span>{bookings.length} total</span></div></div>
        {bookings.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Booking</th><th>Merchant</th><th>Booked</th><th>Amount</th><th>Status</th><th>Confirmation</th><th /></tr></thead><tbody>{bookings.map((b: any) => <tr key={b.id}><td><strong>{b.title}</strong><small>{b.kind} · {b.city || "—"}</small></td><td>{b.merchant_name}<small>{b.merchant_domain}</small></td><td>{dateTime(b.created_at)}</td><td><strong>{money(b.amount)}</strong></td><td><span className={`badge ${b.status === "confirmed" ? "badge-ok" : b.status === "cancelled" ? "badge-muted" : "badge-warn"}`}>{b.status}</span></td><td className="mono">{b.confirmation || "—"}</td><td>{b.status === "confirmed" && <div className="row-actions"><button className="btn btn-sm" onClick={() => setManage({ action: "modify", booking: b })}>Modify</button><button className="btn btn-sm btn-danger" onClick={() => setManage({ action: "cancel", booking: b })}>Cancel</button></div>}</td></tr>)}</tbody></table></div> : <div className="empty-state">No bookings yet. Ask the assistant to find something.</div>}
      </section>

      <section className="history-grid section-card">
        <div className="card"><div className="card-header"><div><div className="card-title">Transaction history</div><div className="card-sub">{state?.ledger?.simulated ? "Simulated ledger events." : "Monad testnet ledger events."}</div></div><a className="text-link" href="/history">Full history</a></div>{recentTx.length ? <div className="compact-list">{recentTx.map((tx: any, i: number) => <div className="compact-row" key={i}><div><strong>{tx.memo || tx.purpose || tx.type || "Transaction"}</strong><small>{dateTime(tx.ts)} · {tx.tx_hash ? (tx.explorer_url ? <a href={tx.explorer_url} target="_blank" rel="noreferrer" className="text-accent">{tx.tx_hash.slice(0, 12)}…</a> : <span title="Simulated transaction id">{tx.tx_hash.slice(0, 12)}… (simulated)</span>) : "—"}</small></div><strong>{money(tx.amount_inr || tx.amount)}</strong></div>)}</div> : <div className="empty-inline">No transactions yet.</div>}</div>
        <div className="card"><div className="card-header"><div><div className="card-title">Audit trail</div><div className="card-sub">What the policy engine decided and why.</div></div><a className="text-link" href="/history">Full trail</a></div>{recentAudit.length ? <div className="compact-list">{recentAudit.map((a: any, i: number) => <div className="compact-row" key={i}><div><strong>{a.message}</strong><small>{dateTime(a.ts)}</small></div><span className={`badge ${a.level === "crit" ? "badge-danger" : a.level === "warn" ? "badge-warn" : "badge-ok"}`}>{a.level}</span></div>)}</div> : <div className="empty-inline">No activity yet.</div>}</div>
      </section>

      {manage && <div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true" aria-label="Manage booking"><div className="card-header"><div><h2>{manage.action === "cancel" ? "Cancel booking" : "Modify booking"}</h2><p>This action goes back through the security gate.</p></div><button className="icon-close" aria-label="Close" onClick={() => setManage(null)}>×</button></div><div className="verify-box"><div className="verify-line"><span>Booking</span><strong>{manage.booking.title}</strong></div><div className="verify-line"><span>Current amount</span><strong>{money(manage.booking.amount)}</strong></div>{manage.action === "modify" && <div className="field"><label htmlFor="units">New quantity</label><input id="units" className="input" type="number" min="1" max="30" defaultValue={manage.booking.units + 1}/></div>}</div><div className="flex gap-2" style={{ marginTop: 18 }}><button className="btn btn-ghost flex-1" onClick={() => setManage(null)}>Back</button><button className="btn btn-primary flex-1" onClick={() => manageBooking(manage.action, manage.booking, manage.action === "modify" ? Number((document.getElementById("units") as HTMLInputElement)?.value) : undefined)} disabled={busy}>{busy ? "Checking…" : "Continue"}</button></div></div></div>}

      {intent && <div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true" aria-label="Transaction security check"><div className="card-header"><div><h2>Transaction security check</h2><p>Review exactly what the agent is asking PayPilot to authorize.</p></div><span className={`badge ${intent.decision?.verdict === "BLOCK" ? "badge-danger" : "badge-warn"}`}>{intent.decision?.verdict}</span></div><div className="verify-box"><div className="verify-line"><span>Purpose</span><strong>{intent.purpose}</strong></div><div className="verify-line"><span>Merchant</span><strong>{intent.merchant_name || intent.merchant_domain || "—"}</strong></div><div className="verify-line"><span>Website</span><strong className="mono">{intent.merchant_domain || "—"}</strong></div><div className="verify-line"><span>Amount</span><strong>{money(intent.amount)}</strong></div><div className="verify-line"><span>Destination</span><strong className="mono">{intent.pay_to ? `${intent.pay_to.slice(0, 10)}…${intent.pay_to.slice(-8)}` : "—"}</strong></div><div className="verify-line"><span>Risk</span><strong>{intent.decision?.risk ?? 0}/100</strong></div></div><div className="reason-list">{(intent.decision?.reasons || []).map((r: any, i: number) => <div key={i} className={`alert-strip ${r.severity === "block" ? "alert-strip-crit" : r.severity === "step_up" ? "alert-strip-warn" : "alert-strip-ok"}`}>{r.message}</div>)}</div>{intent.decision?.verdict === "BLOCK" && <div className="alert-strip alert-strip-crit">This request cannot be approved by the user. The policy engine has blocked it.</div>}<div className="flex gap-2" style={{ marginTop: 18 }}><button className="btn btn-ghost flex-1" onClick={reject} disabled={busy}>Reject</button>{intent.decision?.verdict !== "BLOCK" && <button className="btn btn-primary flex-1" onClick={approve} disabled={busy}>{busy ? "Verifying…" : intent.decision?.verdict === "STEP_UP" ? "Verify with Passkey" : "Approve"}</button>}</div></div></div>}
    </div>
  );
}
