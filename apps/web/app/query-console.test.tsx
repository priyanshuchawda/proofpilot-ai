import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { QueryConsole } from "./query-console";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("submits a workspace query and renders cited evidence", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      query_run_id: "query-run-a",
      answer_text: "ProofPilot requires grounded evidence. [chunk-a]",
      citations: [
        {
          chunk_id: "chunk-a",
          source_filename: "policy.md",
          page_number: null,
          section_heading: "Policy",
          evidence_text: "ProofPilot answers require grounded evidence.",
        },
      ],
      evidence_chunk_ids: ["chunk-a"],
      confidence_label: "medium",
      refusal_reason: null,
      live_grounding_used: false,
      mode: "verified",
      route: "route_document_verified",
      freshness_label: "not_required",
      contradictions: [],
      cache_status: "miss",
    }),
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<QueryConsole />);

  fireEvent.change(screen.getByLabelText("Workspace ID"), {
    target: { value: "workspace-a" },
  });
  fireEvent.change(screen.getByLabelText("Question"), {
    target: { value: "What does ProofPilot require?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Verified Mode" }));
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));

  await waitFor(() => {
    expect(screen.getByText("ProofPilot requires grounded evidence. [chunk-a]")).toBeVisible();
  });
  expect(screen.getByText("chunk-a")).toBeVisible();
  expect(screen.getByText("policy.md")).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith(
    "http://localhost:8000/api/v1/workspaces/workspace-a/query",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        query: "What does ProofPilot require?",
        mode: "verified",
      }),
    }),
  );
});
