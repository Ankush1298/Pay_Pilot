"use client";

import { LazyMotion, MotionConfig, domAnimation } from "framer-motion";
import { ReactNode } from "react";
import { AuthProvider } from "@/components/AuthContext";
import { CookieBanner } from "@/components/CookieBanner";
import { ToastProvider } from "@/components/ToastContext";

export function ClientProviders({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      <MotionConfig reducedMotion="user">
        <ToastProvider>
          <AuthProvider>
            {children}
            <CookieBanner />
          </AuthProvider>
        </ToastProvider>
      </MotionConfig>
    </LazyMotion>
  );
}
