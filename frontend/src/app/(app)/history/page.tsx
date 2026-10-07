"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthContext";
import { useToast } from "@/components/ToastContext";
import { api } from "@/lib/api";

function money(v: any) { return `₹${Number(v || 0).toLocaleString("en-IN")}`; }
function dt(ts: any) { return ts ? new Date(Number(ts) * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "—"; }

export default function HistoryPage() {
  const { user } = useAuth();
  const { show } = useToast();
  const [s, setS] = useState<any>(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (user) api.state.get().then(setS).catch((e: any) => show("crit", e.message)); }, [user]);
  if (!user || !s) return null;
  const bookings = s.bookings || [];
  const txs = s.ledger?.txs || [];
  const audit = s.audit || [];
  return <div className="page">
    <div className="page-header"><div><div className="eyebrow">ACCOUNT HISTORY</div><h1>Activity & history</h1><p>A complete view of bookings, money movement and security decisions.</p></div></div>
    <section className="history-stats"><div className="card"><span className="stat-label">Bookings</span><strong className="big-stat">{bookings.length}</strong><span className="stat-sub">Confirmed + cancelled</span></div><div className="card"><span className="stat-label">Transactions</span><strong className="big-stat">{txs.length}</strong><span className="stat-sub">{s.ledger?.simulated ? "Simulated ledger transactions" : "Monad testnet transactions"}</span></div><div className="card"><span className="stat-label">Security events</span><strong className="big-stat">{audit.length}</strong><span className="stat-sub">Policy decisions and actions</span></div></section>
    <section className="card section-card"><div className="card-header"><div><div className="card-title">Booking history</div><div className="card-sub">Nothing disappears after cancellation.</div></div></div>{bookings.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Booked</th><th>Item</th><th>Merchant</th><th>Amount</th><th>Status</th><th>Confirmation</th></tr></thead><tbody>{bookings.map((b:any)=><tr key={b.id}><td>{dt(b.created_at)}</td><td><strong>{b.title}</strong><small>{b.kind} · {b.city || "—"}</small></td><td>{b.merchant_name}<small>{b.merchant_domain}</small></td><td>{money(b.amount)}</td><td><span className={`badge ${b.status === "confirmed" ? "badge-ok" : "badge-muted"}`}>{b.status}</span></td><td className="mono">{b.confirmation || "—"}</td></tr>)}</tbody></table></div> : <div className="empty-state">No bookings yet.</div>}</section>
    <div className="history-grid section-card"><section className="card"><div className="card-header"><div><div className="card-title">Transaction history</div><div className="card-sub">Latest first.</div></div></div><div className="timeline">{txs.map((t:any,i:number)=><div className="timeline-row" key={i}><span className="timeline-dot"/><div><strong>{t.memo || "Transaction"}</strong><span>{dt(t.ts)} · {money(t.amount_inr)} · {t.tx_hash ? (t.explorer_url ? <a href={t.explorer_url} target="_blank" rel="noreferrer" className="text-accent">{t.tx_hash.slice(0, 14)}…</a> : <span title="Simulated transaction id">{t.tx_hash.slice(0, 14)}… (simulated)</span>) : "no tx hash"}</span></div></div>)}{!txs.length&&<div className="empty-inline">No transactions.</div>}</div></section><section className="card"><div className="card-header"><div><div className="card-title">Security audit</div><div className="card-sub">Independent policy trail.</div></div></div><div className="timeline">{audit.map((a:any,i:number)=><div className="timeline-row" key={i}><span className={`timeline-dot ${a.level}`}/><div><strong>{a.message}</strong><span>{dt(a.ts)}</span></div></div>)}{!audit.length&&<div className="empty-inline">No audit events.</div>}</div></section></div>
  </div>;
}
