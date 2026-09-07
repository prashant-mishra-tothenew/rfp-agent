import type { CSSProperties } from "react";
import Link from "next/link";

const linkStyle: CSSProperties = {
  color: "white",
  textDecoration: "none",
  opacity: 0.85,
  fontSize: "0.875rem",
};

const activeLinkStyle: CSSProperties = {
  ...linkStyle,
  opacity: 1,
  fontWeight: 600,
  borderBottom: "2px solid white",
  paddingBottom: 2,
};

export function AppNav({ active }: { active: "rfp" | "knowledge" }) {
  return (
    <nav style={{ display: "flex", gap: "1.5rem", marginTop: "0.75rem" }}>
      <Link href="/" style={active === "rfp" ? activeLinkStyle : linkStyle}>
        New RFP
      </Link>
      <Link
        href="/knowledge"
        style={active === "knowledge" ? activeLinkStyle : linkStyle}
      >
        Knowledge Base
      </Link>
    </nav>
  );
}
