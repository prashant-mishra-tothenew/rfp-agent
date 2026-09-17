"use client";

import { AppHeader } from "@/components/AppHeader";
import { RfpActorProvider } from "@/components/RfpActorProvider";

export function ClientShell({ children }: { children: React.ReactNode }) {
  return (
    <RfpActorProvider>
      <AppHeader />
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "2rem" }}>
        {children}
      </main>
    </RfpActorProvider>
  );
}
