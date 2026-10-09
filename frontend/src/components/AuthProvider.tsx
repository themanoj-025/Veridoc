"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/lib/store";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const checkAuth = useAuthStore((s) => s.checkAuth);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return <>{children}</>;
}
