export type RfpActorRole = "sme" | "user";

export const RFP_OWNER_ID = "demo_rfp_user";

const STORAGE_KEY = "rfp_actor_role";

export const RFP_ROLE_OPTIONS: Array<{
  role: RfpActorRole;
  label: string;
  description: string;
}> = [
  {
    role: "sme",
    label: "Reviewer",
    description: "View and review all RFPs",
  },
  {
    role: "user",
    label: "Contributor",
    description: "View only your own RFPs",
  },
];

export function getStoredRfpRole(): RfpActorRole {
  if (typeof window === "undefined") return "user";
  const raw = window.localStorage.getItem(STORAGE_KEY);
  return raw === "sme" ? "sme" : "user";
}

export function setStoredRfpRole(role: RfpActorRole): void {
  window.localStorage.setItem(STORAGE_KEY, role);
  window.dispatchEvent(new CustomEvent("rfp-actor-changed", { detail: { role } }));
}

export function rfpActorHeaders(): Record<string, string> {
  const role = getStoredRfpRole();
  return {
    "X-RFP-Role": role,
    "X-RFP-Owner-Id": RFP_OWNER_ID,
  };
}

export function rfpActorQueryString(): string {
  const role = getStoredRfpRole();
  const params = new URLSearchParams({
    role,
    ownerId: RFP_OWNER_ID,
  });
  return params.toString();
}
