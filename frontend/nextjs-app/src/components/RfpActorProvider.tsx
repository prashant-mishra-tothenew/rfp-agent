"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  getStoredRfpRole,
  RfpActorRole,
  setStoredRfpRole,
} from "@/lib/rfpActor";

interface RfpActorContextValue {
  role: RfpActorRole;
  setRole: (role: RfpActorRole) => void;
  /** Increments when role changes so lists can refetch. */
  revision: number;
}

const RfpActorContext = createContext<RfpActorContextValue | null>(null);

export function RfpActorProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<RfpActorRole>("user");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    setRoleState(getStoredRfpRole());
    const onChange = () => {
      setRoleState(getStoredRfpRole());
      setRevision((n) => n + 1);
    };
    window.addEventListener("rfp-actor-changed", onChange);
    return () => window.removeEventListener("rfp-actor-changed", onChange);
  }, []);

  const setRole = useCallback((next: RfpActorRole) => {
    setStoredRfpRole(next);
    setRoleState(next);
    setRevision((n) => n + 1);
  }, []);

  const value = useMemo(
    () => ({ role, setRole, revision }),
    [role, setRole, revision]
  );

  return (
    <RfpActorContext.Provider value={value}>{children}</RfpActorContext.Provider>
  );
}

export function useRfpActor(): RfpActorContextValue {
  const ctx = useContext(RfpActorContext);
  if (!ctx) {
    throw new Error("useRfpActor must be used within RfpActorProvider");
  }
  return ctx;
}
