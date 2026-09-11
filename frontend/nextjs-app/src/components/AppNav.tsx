import { WorkspaceTab, WorkspaceTabs } from "@/components/WorkspaceTabs";

export function AppNav({ active }: { active: WorkspaceTab }) {
  return (
    <div style={{ marginTop: "0.75rem" }}>
      <WorkspaceTabs active={active} mode="link" />
    </div>
  );
}
