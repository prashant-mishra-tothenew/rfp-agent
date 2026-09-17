export type RfpRole = "sme" | "user";

/** Demo owner id for normal RFP users (TL, etc.) when using the role switcher. */
export const DEFAULT_RFP_OWNER_ID = "demo_rfp_user";

export interface RfpAccessContext {
  role: RfpRole;
  ownerId: string;
}

function headerValue(
  headers: Record<string, string | string[] | undefined>,
  name: string
): string {
  const raw = headers[name] ?? headers[name.toLowerCase()];
  if (Array.isArray(raw)) return raw[0] ?? "";
  return raw ?? "";
}

export function parseRfpAccess(
  headers: Record<string, string | string[] | undefined>,
  query?: { role?: string; ownerId?: string }
): RfpAccessContext {
  const roleRaw = (
    headerValue(headers, "x-rfp-role") ||
    String(query?.role ?? "")
  ).toLowerCase();
  const ownerId = (
    headerValue(headers, "x-rfp-owner-id") ||
    String(query?.ownerId ?? "")
  ).trim() || DEFAULT_RFP_OWNER_ID;
  return {
    role: roleRaw === "sme" ? "sme" : "user",
    ownerId,
  };
}

export function canAccessRfpOwner(
  ownerId: string | null | undefined,
  access: RfpAccessContext
): boolean {
  if (access.role === "sme") return true;
  return ownerId === access.ownerId;
}

/** Reviewers only see contributor RFPs after publish (legacy rows default to published). */
export function isRfpVisibleToReviewer(
  submissionStatus: string | null | undefined
): boolean {
  const status = submissionStatus || "published";
  return status === "published";
}
