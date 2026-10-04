"use client";

import { AuthProvider } from "@/components/AuthContext";
import { ToastProvider } from "@/components/ToastContext";
import { AppLayout } from "@/components/AppLayout";
import { ReactNode } from "react";

export function ClientProviders({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <AuthProvider>
        <AppLayout>
          {children}
        </AppLayout>
      </AuthProvider>
    </ToastProvider>
  );
}

