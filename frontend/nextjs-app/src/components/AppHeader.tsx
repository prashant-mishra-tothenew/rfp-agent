"use client";

import { useRfpActor } from "@/components/RfpActorProvider";
import { RFP_ROLE_OPTIONS, RfpActorRole } from "@/lib/rfpActor";

export function AppHeader() {
  const { role, setRole } = useRfpActor();
  const active = RFP_ROLE_OPTIONS.find((o) => o.role === role);

  return (
    <header
      style={{
        background: "#0f172a",
        color: "white",
        padding: "1rem 2rem",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "1.5rem",
        flexWrap: "wrap",
      }}
    >
      <div>
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>RFP Response Accelerator</h1>
        <p style={{ margin: "0.25rem 0 0", opacity: 0.8, fontSize: "0.875rem" }}>
          AI reuses institutional knowledge safely
        </p>
      </div>

      <div style={{ textAlign: "right", minWidth: 260 }}>
        <label
          htmlFor="rfp-role-select"
          style={{
            display: "block",
            fontSize: "0.7rem",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            opacity: 0.75,
            marginBottom: 4,
          }}
        >
          Acting as
        </label>
        <select
          id="rfp-role-select"
          value={role}
          onChange={(e) => setRole(e.target.value as RfpActorRole)}
          style={{
            width: "100%",
            maxWidth: 320,
            padding: "0.45rem 0.6rem",
            borderRadius: 8,
            border: "1px solid #334155",
            background: "#1e293b",
            color: "white",
            fontSize: "0.875rem",
            cursor: "pointer",
          }}
        >
          {RFP_ROLE_OPTIONS.map((opt) => (
            <option key={opt.role} value={opt.role}>
              {opt.label}
            </option>
          ))}
        </select>
        {active && (
          <p style={{ margin: "0.35rem 0 0", fontSize: "0.75rem", opacity: 0.7 }}>
            {active.description}
          </p>
        )}
      </div>
    </header>
  );
}
