"use client";

import { useState } from "react";

import { EvaluationDashboard } from "./evaluation-dashboard";
import { QueryConsole } from "./query-console";
import { WorkspacePanel } from "./workspace-panel";

export function DashboardWorkflow() {
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");

  return (
    <>
      <WorkspacePanel
        onSelectWorkspace={setSelectedWorkspaceId}
        selectedWorkspaceId={selectedWorkspaceId}
      />
      <QueryConsole workspaceId={selectedWorkspaceId || undefined} />
      <EvaluationDashboard />
    </>
  );
}
