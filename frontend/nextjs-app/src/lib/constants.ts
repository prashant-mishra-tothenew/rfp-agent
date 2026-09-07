export const INDUSTRIES = [
  "Banking",
  "Healthcare",
  "Government",
  "Retail",
  "Technology",
  "Manufacturing",
  "Other",
] as const;

export const DOCUMENT_TYPES = [
  { value: "historical", label: "Historical RFP" },
  { value: "proposal", label: "Proposal Response" },
  { value: "case_study", label: "Case Study" },
  { value: "technical", label: "Technical Document" },
  { value: "capability", label: "Company Capability" },
  { value: "security", label: "Security / Compliance" },
] as const;

export const APPROVAL_STATUSES = [
  { value: "approved", label: "Approved" },
  { value: "current", label: "Current" },
  { value: "draft", label: "Draft" },
  { value: "historical", label: "Historical reference only" },
  { value: "expired", label: "Expired" },
] as const;
