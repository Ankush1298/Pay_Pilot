"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthContext";
import { IconHome, IconSettings, IconLogOut, IconActivity } from "./Icons";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  if (!user) return <>{children}</>;

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h2>IntentLock</h2>
          <p>Secure Agentic Payments</p>
        </div>
        <nav className="flex-col gap-1" style={{ padding: "0 0.5rem" }}>
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
          <div className="text-muted text-sm">
            Wallet: <span className="text-mono">{user.wallet_address ? `${user.wallet_address.substring(0, 8)}...${user.wallet_address.substring(36)}` : 'Loading...'}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="badge badge-info">{(user as any).ledger_network === "monad-testnet" ? "Monad Testnet · live settlement" : "Simulated ledger · no real funds"}</span>
            <span>{user.username}</span>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
