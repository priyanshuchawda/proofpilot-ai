import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { QueryConsole } from "./query-console";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("submits a workspace query and renders cited evidence", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    body: queryStream({
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
    ok: true,
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
  expect(screen.getAllByText("chunk-a")[0]).toBeVisible();
  expect(screen.getByText("policy.md")).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/api/v1/workspaces/workspace-a/query/stream",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        query: "What does ProofPilot require?",
        mode: "verified",
      }),
    }),
  );
});

test("renders answer deltas from the streamed query response", async () => {
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(
        encoder.encode('event: answer_delta\ndata: {"text":"ProofPilot streams "}\n\n'),
      );
      controller.enqueue(
        encoder.encode('event: answer_delta\ndata: {"text":"grounded answers. [chunk-a]"}\n\n'),
      );
      controller.enqueue(
        encoder.encode(
          `event: final\ndata: ${JSON.stringify({
            query_run_id: "query-run-stream",
            answer_text: "ProofPilot streams grounded answers. [chunk-a]",
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
          })}\n\n`,
        ),
      );
      controller.close();
    },
  });
  const fetchMock = vi.fn().mockResolvedValue({
    body: stream,
    ok: true,
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<QueryConsole />);

  fireEvent.change(screen.getByLabelText("Workspace ID"), {
    target: { value: "workspace-a" },
  });
  fireEvent.change(screen.getByLabelText("Question"), {
    target: { value: "What does ProofPilot stream?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Verified Mode" }));
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));

  await waitFor(() => {
    expect(screen.getByText("ProofPilot streams grounded answers. [chunk-a]")).toBeVisible();
  });
  expect(screen.getAllByText("chunk-a")[0]).toBeVisible();
});

test("uses the selected workspace id when provided by the dashboard", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    body: queryStream({
      query_run_id: "query-run-selected",
      answer_text: "Selected workspace answer. [chunk-a]",
      citations: [],
      evidence_chunk_ids: [],
      confidence_label: "medium",
      refusal_reason: null,
      live_grounding_used: false,
      mode: "fast",
      route: "route_document_fast",
      freshness_label: "not_required",
      contradictions: [],
      cache_status: "miss",
    }),
    ok: true,
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<QueryConsole workspaceId="workspace-selected" />);

  fireEvent.change(screen.getByLabelText("Question"), {
    target: { value: "Use selected workspace?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));

  await waitFor(() => {
    expect(screen.getByText("Selected workspace answer. [chunk-a]")).toBeVisible();
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/api/v1/workspaces/workspace-selected/query/stream",
    expect.objectContaining({ method: "POST" }),
  );
});

test("renders a retrieval trace from the final streamed answer", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      body: queryStream({
        query_run_id: "query-run-trace",
        answer_text: "Traceable answer. [chunk-a]",
        citations: [
          {
            chunk_id: "chunk-a",
            document_id: "doc-a",
            source_filename: "policy.md",
            page_number: 2,
            section_heading: "Eligibility",
            evidence_text: "Only cited facts are shown.",
          },
        ],
        evidence_chunk_ids: ["chunk-a", "chunk-b"],
        confidence_label: "high",
        refusal_reason: null,
        live_grounding_used: false,
        mode: "verified",
        route: "route_document_verified",
        freshness_label: "not_required",
        contradictions: [{ claim_key: "pricing", candidate_chunk_ids: ["chunk-a", "chunk-b"] }],
        cache_status: "miss",
      }),
      ok: true,
    }),
  );

  render(<QueryConsole workspaceId="workspace-trace" />);

  fireEvent.change(screen.getByLabelText("Question"), {
    target: { value: "Show trace?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Verified Mode" }));
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));

  let trace: HTMLElement;
  await waitFor(() => {
    trace = screen.getByRole("region", { name: "Retrieval trace" });
    expect(trace).toBeVisible();
  });
  expect(within(trace!).getByText("route_document_verified")).toBeVisible();
  expect(within(trace!).getByText("miss")).toBeVisible();
  expect(within(trace!).getByText("query-run-trace")).toBeVisible();
  expect(within(trace!).getByText("chunk-a, chunk-b")).toBeVisible();
  expect(within(trace!).getByText("pricing")).toBeVisible();
});

function queryStream(finalPayload: object) {
  return new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(encoder.encode('event: answer_delta\ndata: {"text":"streaming"}\n\n'));
      controller.enqueue(
        encoder.encode(`event: final\ndata: ${JSON.stringify(finalPayload)}\n\n`),
      );
      controller.close();
    },
  });
}
