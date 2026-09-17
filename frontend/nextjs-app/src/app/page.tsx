"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { KnowledgeUploadPanel } from "@/components/KnowledgeUploadPanel";
import { RfpReviewQueue } from "@/components/RfpReviewQueue";
import { RfpUploadPanel } from "@/components/RfpUploadPanel";
import {
  WorkspaceTab,
  WorkspaceTabs,
} from "@/components/WorkspaceTabs";

function HomeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tabParam = searchParams.get("tab");
  const activeTab: WorkspaceTab =
    tabParam === "knowledge" ? "knowledge" : "generate";

  const handleTabChange = useCallback(
    (tab: WorkspaceTab) => {
      const query = tab === "knowledge" ? "?tab=knowledge" : "";
      router.replace(`/${query}`, { scroll: false });
    },
    [router]
  );

  return (
    <div>
      <WorkspaceTabs
        active={activeTab}
        mode="button"
        onChange={handleTabChange}
      />

      <div style={{ marginTop: "1.5rem" }}>
        {activeTab === "generate" ? (
          <>
            <RfpReviewQueue />
            <RfpUploadPanel />
          </>
        ) : (
          <KnowledgeUploadPanel />
        )}
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <Suspense fallback={<div style={{ padding: "2rem 0" }}>Loading…</div>}>
      <HomeContent />
    </Suspense>
  );
}
