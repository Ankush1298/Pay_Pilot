"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthContext";
import { copyText } from "@/lib/copy";
import { IconHome, IconSettings, IconLogOut, IconActivity } from "./Icons";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, pathname, router]);

  if (!user) return <div className="auth-wrap" role="status" aria-label="Loading"><div className="spinner" /></div>;

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h2>PayPilot</h2>
          <p>Secure Agentic Payments</p>
        </div>
        <nav aria-label="Main" className="flex-col gap-1" style={{ padding: "0 0.5rem" }}>
          <Link href="/dashboard" className={`nav-item ${pathname === "/dashboard" ? "active" : ""}`}>
            <IconHome />
            Dashboard
          </Link>
          <Link href="/history" className={`nav-item ${pathname === "/history" ? "active" : ""}`}>
            <IconActivity />
            History
          </Link>
          <Link href="/lab" className={`nav-item ${pathname === "/lab" ? "active" : ""}`}>
            <IconActivity />
            Security Lab
          </Link>
          <Link href="/settings" className={`nav-item ${pathname === "/settings" ? "active" : ""}`}>
            <IconSettings />
            Policy Settings
          </Link>
        </nav>
        <div style={{ marginTop: "auto", padding: "1rem 0.5rem" }}>
          <button onClick={handleLogout} className="nav-item">
            <IconLogOut />
            Sign out
          </button>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <strong className="mobile-brand">PayPilot</strong>
          <div className="text-muted text-sm">
            Wallet: <button type="button" className="text-mono" title="Click to copy full address" style={{ background: "none", border: 0, padding: 0, color: "inherit", cursor: "pointer", textDecoration: "underline dotted" }} disabled={!user.wallet_address} onClick={() => user.wallet_address && copyText(user.wallet_address)}>{user.wallet_address ? `${user.wallet_address.substring(0, 8)}...${user.wallet_address.substring(36)}` : 'Loading...'}</button>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="badge badge-info">{(user as any).ledger_network === "monad-testnet" ? "Monad Testnet · live settlement" : "Simulated ledger · no real funds"}</span>
            <span>{user.username}</span>
          </div>
        </header>
        {children}
      </main>
      <nav className="mobile-nav" aria-label="Main (mobile)">
        <Link href="/dashboard" className={pathname === "/dashboard" ? "active" : ""}><IconHome /><span>Dashboard</span></Link>
        <Link href="/history" className={pathname === "/history" ? "active" : ""}><IconActivity /><span>History</span></Link>
        <Link href="/lab" className={pathname === "/lab" ? "active" : ""}><IconActivity /><span>Lab</span></Link>
        <Link href="/settings" className={pathname === "/settings" ? "active" : ""}><IconSettings /><span>Policy</span></Link>
        <button type="button" onClick={handleLogout}><IconLogOut /><span>Sign out</span></button>
      </nav>
    </div>
  );
}
