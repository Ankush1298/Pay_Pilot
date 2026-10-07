"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, m as mo } from "framer-motion";
import { api } from "@/lib/api";
import type { ChatContext, Conversation, Msg } from "@/lib/types";
import { useToast } from "./ToastContext";

const money = (v: number | string | null | undefined) => `₹${Number(v || 0).toLocaleString("en-IN")}`;
const clock = (ts: number) => new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const WELCOME: Msg = { role: "agent", ts: Date.now() / 1000, content: "Tell me what you want to book, for example “book a hotel in Jaipur under ₹1,500 for tomorrow”. I remember what you tell me in this chat, and I’ll ask for the city or date rather than guess." };

/** Reveals text word by word (streaming feel). Skipped for history and for reduced-motion users. */
function Streamed({ text, animate, onDone }: { text: string; animate: boolean; onDone?: () => void }) {
  const words = text.split(" ");
  const [n, setN] = useState(animate ? 0 : words.length);
  useEffect(() => {
    if (!animate || (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches)) { setN(words.length); onDone?.(); return; }
    const t = setInterval(() => setN((x) => { if (x + 2 >= words.length) { clearInterval(t); onDone?.(); return words.length; } return x + 2; }), 35);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, animate]);
  return <>{words.slice(0, n).join(" ")}</>;
}

function chips(ctx: ChatContext): { key: string; label: string; value: string; edit?: string; clearable: boolean }[] {
  const c: { key: string; label: string; value: string; edit?: string; clearable: boolean }[] = [];
  if (ctx.city) c.push({ key: "city", label: "City", value: ctx.city, edit: ctx.city, clearable: true });
  if (ctx.dates) c.push({ key: "dates", label: "Dates", value: ctx.dates.text, edit: ctx.dates.text, clearable: true });
  if (ctx.budget != null) c.push({ key: "budget", label: "Budget", value: money(ctx.budget), edit: String(ctx.budget), clearable: true });
  if (ctx.guests) c.push({ key: "guests", label: "Guests", value: String(ctx.guests), edit: String(ctx.guests), clearable: true });
  if (ctx.merchant) c.push({ key: "merchant", label: "Merchant", value: ctx.merchant, edit: ctx.merchant, clearable: true });
  if (ctx.currency) c.push({ key: "currency", label: "Currency", value: ctx.currency, clearable: false });
  if (ctx.last_selected?.title) c.push({ key: "last", label: "Last selected", value: ctx.last_selected.title, clearable: false });
  return c;
}

export function ChatPanel({ onBook, busy, refreshKey }: { onBook: (optionId: string, conversationId?: string) => void; busy: boolean; refreshKey: number }) {
  const { show } = useToast();
  const [convs, setConvs] = useState<Conversation[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([WELCOME]);
  const [ctx, setCtx] = useState<ChatContext>({});
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [drawer, setDrawer] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [editVal, setEditVal] = useState("");
  const [typing, setTyping] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  const openConv = useCallback(async (id: string) => {
    try {
      const c = await api.chats.get(id);
      setActive(id); setCtx(c.context || {}); setDrawer(false);
      setMsgs(c.messages.length ? c.messages : [WELCOME]);
    } catch (e: any) { show("crit", e.message || "Could not open that chat"); }
  }, [show]);

  const loadList = useCallback(async () => { const l: Conversation[] = await api.chats.list(); setConvs(l); return l; }, []);

  useEffect(() => {
    (async () => {
      try { const l = await loadList(); if (l[0]) await openConv(l[0].id); }
      catch (e: any) { show("crit", e.message || "Could not load your chats"); }
      finally { setLoading(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { if (active && refreshKey) api.chats.get(active).then((c) => setCtx(c.context || {})).catch(() => {}); }, [refreshKey, active]);
  // Scroll only the message list: scrollIntoView would also drag the whole page down (visible on phones).
  useEffect(() => { const list = bottom.current?.parentElement; if (list) list.scrollTo({ top: list.scrollHeight, behavior: "smooth" }); }, [msgs, typing]);

  const newChat = async () => {
    try { const c = await api.chats.create(); setActive(c.id); setCtx({}); setMsgs([WELCOME]); setDrawer(false); await loadList(); }
    catch (e: any) { show("crit", e.message || "Could not start a new chat"); }
  };

  const removeConv = async (id: string) => {
    try { await api.chats.remove(id); const l = await loadList(); if (id === active) { if (l[0]) await openConv(l[0].id); else { setActive(null); setCtx({}); setMsgs([WELCOME]); } } }
    catch (e: any) { show("crit", e.message || "Could not delete the chat"); }
  };

  const send = async (text: string, retryTs?: number) => {
    const t = text.trim();
    if (!t || sending) return;
    const ts = retryTs ?? Date.now() / 1000;
    setInput("");
    setMsgs((x) => [...(retryTs ? x.filter((m) => !(m.failed && m.ts === retryTs)) : x), { role: "user", content: t, ts }]);
    setSending(true); setTyping(true);
    try {
      const r = await api.agent.chat(t, active ?? undefined);
      setActive(r.conversation_id); setCtx(r.context || {});
      setMsgs((x) => [...x, { role: "agent", content: r.text, ts: Date.now() / 1000, options: r.options, browsed: r.browsed, resolved: r.resolved, needs: r.needs, fresh: true }]);
      loadList().catch(() => {});
    } catch (e: any) {
      setMsgs((x) => x.map((m) => (m.role === "user" && m.ts === ts ? { ...m, failed: true } : m)));
      show("crit", e.message || "The assistant could not answer");
    } finally { setSending(false); setTyping(false); }
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(input); }
  };

  const applyEdit = async (key: string, value: string | null) => {
    if (!active) return;
    let v: unknown = value;
    if (value !== null && key === "budget") v = Number(value.replace(/[₹,\s]/g, ""));
    if (value !== null && key === "guests") v = parseInt(value, 10);
    try { setCtx(await api.chats.editContext(active, { [key]: v })); setEditing(null); }
    catch (e: any) { show("warn", e.message || "That value isn't valid"); }
  };

  const copy = async (text: string) => {
    try { await navigator.clipboard.writeText(text); show("ok", "Copied"); } catch { show("warn", "Copy isn't available in this browser"); }
  };

  const list = chips(ctx);
  return (
    <section className="card chat-card chat-with-list">
      <aside className={`conv-list ${drawer ? "open" : ""}`} aria-label="Conversations">
        <button className="btn btn-primary btn-sm btn-full" onClick={newChat}>+ New chat</button>
        <ul>
          {convs.map((c) => (
            <li key={c.id} className={c.id === active ? "on" : ""}>
              <button className="conv-open" onClick={() => openConv(c.id)} aria-current={c.id === active}>{c.title}<small>{new Date(c.updated * 1000).toLocaleDateString()}</small></button>
              <button className="conv-del" aria-label={`Delete chat ${c.title}`} onClick={() => removeConv(c.id)}>×</button>
            </li>
          ))}
          {!convs.length && !loading && <li className="empty-inline">No chats yet.</li>}
        </ul>
      </aside>
      <div className="chat-main">
        <div className="chat-head">
          <div><div className="card-title">AI booking assistant</div><div className="card-sub"><span className="status-dot" /> No payment key · cannot approve its own request</div></div>
          <div className="flex gap-2 items-center">
            <button className="btn btn-sm btn-ghost chat-toggle" onClick={() => setDrawer((d) => !d)} aria-expanded={drawer}>Chats</button>
            <button className="btn btn-sm btn-secondary" onClick={newChat}>New chat</button>
          </div>
        </div>
        <div className="chat-wrap" role="log" aria-live="polite" aria-label="Conversation">
          {loading && <div className="chat-bubble agent"><div className="progress-dots"><span /><span /><span /></div></div>}
          {msgs.map((m, i) => {
            const last = i === msgs.length - 1;
            return (
              <mo.div key={m.id ?? `${m.ts}-${i}`} className={`chat-bubble ${m.role}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                <div className="msg-text"><Streamed text={m.content} animate={!!m.fresh && last} /></div>
                {m.resolved && m.resolved.length > 0 && (
                  <div className="resolved-note">Used from earlier in this chat: {m.resolved.map((r) => `${r.field} ${typeof r.value === "number" ? money(r.value) : r.value}`).join(" · ")}</div>
                )}
                {m.browsed?.length ? <div className="browse-list"><div className="browse-heading">Browsing activity</div>{m.browsed.map((b, j) => <div className="browse-row" key={j}><span className={`badge ${b.status === "ok" ? "badge-ok" : b.status === "flagged" ? "badge-danger" : "badge-warn"}`}>{b.status}</span><span className="browse-domain">{b.domain}</span><span className="browse-note">{b.note}</span></div>)}</div> : null}
                {m.options?.length ? (
                  <div className="option-grid">
                    {m.options.map((o) => (
                      <div className={`option-card ${o.best ? "best" : ""}`} key={o.id} role="button" tabIndex={0} aria-label={`Review and book ${o.title}`} onClick={() => !busy && onBook(o.id, active ?? undefined)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (!busy) onBook(o.id, active ?? undefined); } }}>
                        {o.best && <span className="best-badge">BEST MATCH</span>}
                        <div className="option-title">{o.title}</div>
                        <div className="option-meta">{o.merchant_name} · {o.city}</div>
                        <div className="rating">★ {o.rating ?? "—"} · {(o.reviews || 0).toLocaleString()} reviews</div>
                        <div className="option-price">{money(o.total)}</div>
                        <div className="option-meta">{o.perks || "Standard terms"}</div>
                        <span className="btn btn-secondary btn-sm" style={{ marginTop: 9 }}>Review &amp; book</span>
                      </div>
                    ))}
                  </div>
                ) : null}
                <div className="msg-meta">
                  <time dateTime={new Date(m.ts * 1000).toISOString()}>{clock(m.ts)}</time>
                  <button className="link-btn" onClick={() => copy(m.content)} aria-label="Copy message">Copy</button>
                  {m.failed && <button className="link-btn retry" onClick={() => send(m.content, m.ts)}>Failed. Retry</button>}
                </div>
              </mo.div>
            );
          })}
          <AnimatePresence>{typing && (
            <mo.div key="typing" className="chat-bubble agent" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} aria-label="Assistant is typing"><div className="progress-dots"><span /><span /><span /></div></mo.div>
          )}</AnimatePresence>
          <div ref={bottom} />
        </div>
        <div className="chip-row" aria-label="What the assistant currently assumes">
          {list.length === 0 && <span className="chip-hint">Nothing remembered yet. Say a city, dates or budget.</span>}
          {list.map((c) => (
            <span className="ctx-chip" key={c.key}>
              {editing === c.key ? (
                <form onSubmit={(e) => { e.preventDefault(); applyEdit(c.key, editVal); }}>
                  <label className="sr-only" htmlFor={`chip-${c.key}`}>{c.label}</label>
                  <input id={`chip-${c.key}`} autoFocus value={editVal} onChange={(e) => setEditVal(e.target.value)} onBlur={() => setEditing(null)} onKeyDown={(e) => { if (e.key === "Escape") setEditing(null); }} />
                </form>
              ) : c.edit !== undefined ? (
                <button type="button" className="chip-label" onClick={() => { setEditing(c.key); setEditVal(c.edit ?? ""); }} aria-label={`Edit ${c.label}: ${c.value}`}>{c.label}: {c.value}</button>
              ) : (<span className="chip-label static">{c.label}: {c.value}</span>)}
              {c.clearable && <button type="button" className="chip-x" aria-label={`Clear ${c.label}`} onClick={() => applyEdit(c.key, null)}>✕</button>}
            </span>
          ))}
        </div>
        <form className="chat-form" onSubmit={(e) => { e.preventDefault(); send(input); }}>
          <label htmlFor="chat-input" className="sr-only">Message</label>
          <textarea id="chat-input" className="input" rows={1} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKey} placeholder="Book a hotel in Jaipur under ₹1,500 for tomorrow (Enter to send, Shift+Enter for a new line)" maxLength={600} disabled={sending} />
          <button className="btn btn-primary" disabled={sending || !input.trim()}>Send</button>
        </form>
      </div>
    </section>
  );
}
