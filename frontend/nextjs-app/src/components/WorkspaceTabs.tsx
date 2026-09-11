"use client";

import Link from "next/link";

export type WorkspaceTab = "generate" | "knowledge";

const TABS: { id: WorkspaceTab; label: string; description: string }[] = [
  {
    id: "generate",
    label: "Generate RFP",
    description: "Upload a new RFP and run the analysis pipeline",
  },
  {
    id: "knowledge",
    label: "Knowledge Base",
    description: "Upload historical proposals and company documents",
  },
];

export function WorkspaceTabs({
  active,
  mode = "link",
  onChange,
}: {
  active: WorkspaceTab;
  mode?: "link" | "button";
  onChange?: (tab: WorkspaceTab) => void;
}) {
  return (
    <div
      className="workspace-tabs"
      role="tablist"
      aria-label="Workspace sections"
    >
      {TABS.map((tab) => {
        const isActive = active === tab.id;
        const className = `workspace-tab${isActive ? " workspace-tab-active" : ""}`;

        if (mode === "button" && onChange) {
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={className}
              onClick={() => onChange(tab.id)}
            >
              <span className="workspace-tab-label">{tab.label}</span>
              <span className="workspace-tab-desc">{tab.description}</span>
            </button>
          );
        }

        const href = tab.id === "generate" ? "/" : "/?tab=knowledge";
        return (
          <Link
            key={tab.id}
            href={href}
            role="tab"
            aria-selected={isActive}
            className={className}
          >
            <span className="workspace-tab-label">{tab.label}</span>
            <span className="workspace-tab-desc">{tab.description}</span>
          </Link>
        );
      })}
    </div>
  );
}
