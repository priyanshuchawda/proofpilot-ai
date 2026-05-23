import { createProofPilotClient } from "@proofpilot/generated-api-client";

test("generated client posts workspace queries with the typed payload", async () => {
  const fetcher = vi.fn(async () => ({
    ok: true,
    json: async () => ({
      answer_text: "The policy allows uploads.",
      cache_status: "miss",
      citations: [],
      confidence_label: "high",
      contradictions: [],
      evidence_chunk_ids: [],
      freshness_label: "document",
      live_grounding_used: false,
      mode: "fast",
      query_run_id: "run-1",
      refusal_reason: null,
      route: "route_document_fast",
    }),
  })) as unknown as typeof fetch;

  const client = createProofPilotClient({
    baseUrl: "http://api.test",
    fetch: fetcher,
  });

  await client.queryWorkspace("workspace-1", {
    mode: "fast",
    query: "What uploads are allowed?",
  });

  expect(fetcher).toHaveBeenCalledWith(
    "http://api.test/api/v1/workspaces/workspace-1/query",
    expect.objectContaining({
      body: JSON.stringify({ mode: "fast", query: "What uploads are allowed?" }),
      method: "POST",
    }),
  );
});

test("generated client runs deterministic evaluations", async () => {
  const fetcher = vi.fn(async () => ({
    ok: true,
    json: async () => ({
      run_id: "eval-1",
      status: "completed",
      summary: {
        cache_hit_rate: 0,
        case_count: 6,
        citation_validity_rate: 1,
        contradiction_correctness_rate: 1,
        latency_p50_ms: 20,
        latency_p95_ms: 40,
        refusal_correctness_rate: 1,
        retrieval_hit_rate: 1,
        secret_leak_count: 0,
      },
    }),
  })) as unknown as typeof fetch;

  const client = createProofPilotClient({
    baseUrl: "http://api.test/",
    fetch: fetcher,
  });

  const run = await client.runEvaluation();

  expect(run.summary.secret_leak_count).toBe(0);
  expect(fetcher).toHaveBeenCalledWith(
    "http://api.test/api/v1/evaluations/run",
    expect.objectContaining({ method: "POST" }),
  );
});

test("generated client fetches query-run trace details", async () => {
  const fetcher = vi.fn(async () => ({
    ok: true,
    json: async () => ({
      id: "query-run-1",
      workspace_id: "workspace-1",
      query_text: "What was retrieved?",
      route: "route_document_verified",
      mode: "verified",
      cache_status: "miss",
      retrieval_candidates: [
        {
          chunk_id: "chunk-a",
          source: "hybrid",
          rank: 1,
          score: "0.75000000",
          source_filename: "policy.md",
          page_number: null,
          section_heading: "Policy",
        },
      ],
      cited_evidence: [],
      generated_answer: null,
      verification_result: null,
      latency_metrics: [],
    }),
  })) as unknown as typeof fetch;

  const client = createProofPilotClient({
    baseUrl: "http://api.test/",
    fetch: fetcher,
  });

  const trace = await client.getQueryRun("query-run-1");

  expect(trace.retrieval_candidates[0].source).toBe("hybrid");
  expect(fetcher).toHaveBeenCalledWith(
    "http://api.test/api/v1/query-runs/query-run-1",
    expect.objectContaining({ method: "GET" }),
  );
});
