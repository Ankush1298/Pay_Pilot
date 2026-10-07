"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

type AuthContextType = {
  user: any;
  loading: boolean;
  checkAuth: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  checkAuth: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const data = await api.auth.session();      // 200 even when signed out, so no 401 in the console
      setUser(data.authenticated ? data : null);
    } catch (err: any) {
      if (err.code === "no_token" || err.code === "session_expired") {
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } finally {
      setUser(null);
    }
  };

  useEffect(() => {
    checkAuth();
    const drop = () => setUser(null);          // any API call that comes back 401 means the session is gone
    window.addEventListener("paypilot:unauthorized", drop);
    return () => window.removeEventListener("paypilot:unauthorized", drop);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, checkAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
