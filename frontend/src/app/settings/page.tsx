"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthContext";
import { useToast } from "@/components/ToastContext";
import { api } from "@/lib/api";
import { registerPasskey } from "@/lib/passkeys";

export default function SettingsPage() {
  const { user, loading } = useAuth();
  const { show } = useToast();
  const [s, setS] = useState<any>(null);
  const [pkBusy, setPkBusy] = useState(false);

  const load = async () => { try { setS(await api.state.get()); } catch (e: any) { show("crit", e.message || "Failed to load settings"); } };
  useEffect(() => { if (user && !loading) load(); }, [user, loading]);

  const deviceAction = async (id: string, action: "approve" | "block") => {
    try { if (action === "approve") await api.devices.approve(id); else await api.devices.block(id); show("ok", action === "approve" ? "Device approval requested" : "Device blocked"); await load(); }
    catch (e: any) { show("crit", e.message || `Could not ${action} device`); }
  };

  const addPasskey = async () => {
    setPkBusy(true);
    try { await registerPasskey(`${s?.me?.device?.name || "Device"} passkey`); show("ok", "Passkey registered on this device"); await load(); }
    catch (e: any) { show("warn", e.message || "Passkey registration cancelled"); }
    finally { setPkBusy(false); }
  };

  const connect = async (domain: string) => {
    try { const r = await api.connections.start(domain); window.location.href = r.url; }
    catch (e: any) { show("crit", e.message); }
  };
  const disconnect = async (domain: string) => { try { await api.connections.disconnect(domain); show("ok", `Disconnected ${domain}`); await load(); } catch (e:any) { show("crit", e.message); } };

  if (!user || !s) return null;
  const devices = s.devices || [];
  const connections = s.connections || [];
  return <div className="page">
    <div className="page-header"><div><div className="eyebrow">SECURITY SETTINGS</div><h1>Policy & devices</h1><p>Authentication, device trust, merchant connections and the rules enforced outside the AI.</p></div></div>
    <div className="grid-2">
      <section className="card"><div className="card-header"><div><div className="card-title">Registered devices</div><div className="card-sub">New devices can browse, but transactions stay locked until trusted.</div></div><span className="badge badge-info">{devices.length}</span></div>{devices.map((d:any)=><div className="security-row settings-device" key={d.id}><div className="left"><div className="security-icon">{d.status === "trusted" ? "✓" : "!"}</div><div><strong>{d.name}</strong><span>{d.ip || "IP unavailable"} · {d.ua || "Browser"}</span><small>Added {new Date(d.first_seen * 1000).toLocaleDateString()}</small></div></div><div className="flex gap-2 items-center"><span className={`badge ${d.status === "trusted" ? "badge-ok" : d.status === "blocked" ? "badge-danger" : "badge-warn"}`}>{d.status}</span>{d.status === "pending" && d.id !== s.me?.device?.id && <><button className="btn btn-sm btn-success" onClick={() => deviceAction(d.id, "approve")}>Approve</button><button className="btn btn-sm btn-danger" onClick={() => deviceAction(d.id, "block")}>Block</button></>}</div></div>)}
      </section>
      <section className="card"><div className="card-header"><div><div className="card-title">Passkey authentication</div><div className="card-sub">Sensitive payments use a device-bound credential.</div></div><span className={`badge ${s.me?.has_passkey ? "badge-ok" : "badge-warn"}`}>{s.me?.has_passkey ? "Ready" : "Not set"}</span></div><div className="stat-box"><span className="stat-label">Current device</span><span className="stat-value" style={{fontSize:15}}>{s.me?.device?.name || "Current device"}</span><span className="stat-sub">The browser may use Touch ID, Face ID, fingerprint or the device's passkey/PIN.</span></div><button className="btn btn-primary" style={{marginTop:12}} onClick={addPasskey} disabled={pkBusy}>{pkBusy ? "Waiting for device…" : s.me?.has_passkey ? "Register another passkey" : "Set up passkey"}</button></section>
    </div>

    <section className="card section-card"><div className="card-header"><div><div className="card-title">Security policy</div><div className="card-sub">These rules are enforced by the policy engine, not by the AI.</div></div></div><div className="grid-3"><div className="stat-box"><span className="stat-label">Automatic ceiling</span><span className="stat-value">Configured</span><span className="stat-sub">The exact threshold stays private to your policy engine.</span></div><div className="stat-box"><span className="stat-label">24h policy</span><span className="stat-value">Configured</span><span className="stat-sub">Current automatic spend is monitored server-side.</span></div><div className="stat-box"><span className="stat-label">New device hold</span><span className="stat-value">{s.policy.new_device_lock_hours}h</span><span className="stat-sub">Pending devices cannot spend.</span></div></div><div className="stat-box" style={{marginTop:12}}><span className="stat-label">Permitted transaction types</span><div className="flex" style={{flexWrap:"wrap",gap:6,marginTop:8}}>{(s.policy.allowed_types||[]).map((t:string)=><span className="badge badge-muted" key={t}>{t.replace("_"," ")}</span>)}</div></div></section>

    <section className="card section-card"><div className="card-header"><div><div className="card-title">Connected merchants</div><div className="card-sub">Delegated website sessions. PayPilot never stores the merchant password.</div></div></div><div className="merchant-grid">{connections.map((c:any)=><div className="merchant-connection" key={c.domain}><div><strong>{c.domain}</strong><span>{c.member} · {c.scope}</span></div><button className="btn btn-sm btn-danger" onClick={() => disconnect(c.domain)}>Disconnect</button></div>)}{!connections.length&&<div className="empty-inline">No merchant sessions connected. Discovery still works across the demo merchant registry; payment stays gated until the merchant is trusted.</div>}</div><div className="connect-actions"><button className="btn btn-secondary btn-sm" onClick={() => connect("grandstay.mock")}>Connect GrandStay</button><button className="btn btn-secondary btn-sm" onClick={() => connect("cityinn.mock")}>Connect CityInn</button></div></section>
  </div>;
}
