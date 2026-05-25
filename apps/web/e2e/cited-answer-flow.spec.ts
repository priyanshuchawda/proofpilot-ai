import { expect, test } from "@playwright/test";

const apiBaseUrl = "http://127.0.0.1:8000";
const frontendOrigin = "http://127.0.0.1:3013";
const workspaceId = "workspace-e2e";
const documentId = "document-e2e";
const chunkId = "chunk-e2e";
const queryRunId = "query-run-e2e";

test("uploads public evidence and displays a cited verified answer with its trace", async ({
  page,
}) => {
  let workspaceCreated = false;
  let uploadAccepted = false;
  const corsHeaders = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST",
    "Access-Control-Allow-Origin": frontendOrigin,
  };

  await page.route(`${apiBaseUrl}/api/v1/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();

    if (method === "OPTIONS") {
      await route.fulfill({ headers: corsHeaders, status: 204 });
      return;
    }

    if (method === "GET" && url.pathname === "/api/v1/health") {
      await route.fulfill({
        headers: corsHeaders,
        json: { service: "proofpilot-api", status: "ok", version: "0.1.0" },
      });
      return;
    }

    if (method === "GET" && url.pathname === "/api/v1/settings/ai") {
      await route.fulfill({
        headers: corsHeaders,
        json: {
          backend_only: true,
          embedding_dimension: 768,
          embedding_model: "gemini-embedding-2",
          embeddings_enabled: true,
          freshness_model: "gemini-2.5-flash-lite",
          gemini_configured: false,
          generation_model: "gemini-2.5-flash-lite",
          lightweight_model: "gemini-2.5-flash-lite",
          live_smoke_enabled: false,
          search_grounding_enabled: false,
          search_grounding_model: "gemini-2.5-flash-lite",
        },
      });
      return;
    }

    if (method === "GET" && url.pathname === "/api/v1/metrics/operational") {
      await route.fulfill({
        headers: corsHeaders,
        json: {
          dependencies: [
            { detail: null, name: "postgres", status: "ok" },
            { detail: null, name: "redis", status: "ok" },
            { detail: null, name: "qdrant", status: "ok" },
          ],
          telemetry: {
            cache_events: [
              {
                cache_name: "response",
                count: 1,
                mode: "verified",
                result: "miss",
                workspace_hash: "e2e-workspace-hash",
              },
            ],
            gemini_errors: [],
            gemini_requests: [
              {
                count: 1,
                google_search: false,
                model: "gemini-2.5-flash-lite",
                provider: "mock",
              },
            ],
          },
        },
      });
      return;
    }

    if (method === "GET" && url.pathname === "/api/v1/workspaces") {
      await route.fulfill({
        headers: corsHeaders,
        json: workspaceCreated
          ? [
              {
                description: "Non-confidential source",
                id: workspaceId,
                name: "Public decision record",
              },
            ]
          : [],
      });
      return;
    }

    if (method === "POST" && url.pathname === "/api/v1/workspaces") {
      expect(request.postDataJSON()).toEqual({
        description: "Non-confidential source",
        name: "Public decision record",
      });
      workspaceCreated = true;
      await route.fulfill({
        headers: corsHeaders,
        json: {
          description: "Non-confidential source",
          id: workspaceId,
          name: "Public decision record",
        },
      });
      return;
    }

    if (url.pathname === `/api/v1/workspaces/${workspaceId}/documents`) {
      if (method === "POST") {
        uploadAccepted = true;
        await route.fulfill({
          headers: corsHeaders,
          json: {
            chunk_count: 0,
            filename: "public-evidence.md",
            id: documentId,
            mime_type: "text/markdown",
            status: "uploaded",
            workspace_id: workspaceId,
          },
        });
        return;
      }

      if (method === "GET") {
        await route.fulfill({
          headers: corsHeaders,
          json: uploadAccepted
            ? [
                {
                  chunk_count: 1,
                  filename: "public-evidence.md",
                  id: documentId,
                  mime_type: "text/markdown",
                  status: "ready",
                  workspace_id: workspaceId,
                },
              ]
            : [],
        });
        return;
      }
    }

    if (method === "POST" && url.pathname === `/api/v1/workspaces/${workspaceId}/query/stream`) {
      expect(request.postDataJSON()).toEqual({
        mode: "verified",
        query: "What evidence supports the rollout decision?",
      });
      const finalAnswer = {
        answer_text: "The rollout required cited public evidence [chunk-e2e].",
        cache_status: "miss",
        citations: [
          {
            chunk_id: chunkId,
            evidence_text: "The rollout requires documented public evidence before approval.",
            page_number: null,
            section_heading: "Approval",
            source_filename: "public-evidence.md",
            source_kind: "document",
          },
        ],
        confidence_label: "high",
        contradictions: [],
        evidence_chunk_ids: [chunkId],
        freshness_label: "document_snapshot",
        generation_model_used: "gemini-2.5-flash-lite",
        live_grounding_used: false,
        mode: "verified",
        query_run_id: queryRunId,
        refusal_reason: null,
        route: "route_document_verified",
        search_suggestions_html: null,
      };
      await route.fulfill({
        body:
          'event: answer_delta\ndata: {"text":"The rollout required cited public evidence "}\n\n' +
          `event: final\ndata: ${JSON.stringify(finalAnswer)}\n\n`,
        contentType: "text/event-stream",
        headers: corsHeaders,
      });
      return;
    }

    if (method === "GET" && url.pathname === `/api/v1/query-runs/${queryRunId}`) {
      await route.fulfill({
        headers: corsHeaders,
        json: {
          cache_status: "miss",
          cited_evidence: [
            {
              chunk_id: chunkId,
              citation_label: chunkId,
              evidence_text: "The rollout requires documented public evidence before approval.",
              source_kind: "document",
            },
          ],
          generated_answer: {
            answer_text: "The rollout required cited public evidence [chunk-e2e].",
            confidence_label: "high",
            live_grounding_used: false,
            refusal_reason: null,
          },
          id: queryRunId,
          latency_metrics: [{ duration_ms: 17, metric_name: "retrieval" }],
          mode: "verified",
          query_text: "What evidence supports the rollout decision?",
          retrieval_candidates: [
            {
              chunk_id: chunkId,
              rank: 1,
              score: "1.0",
              source: "hybrid",
              source_filename: "public-evidence.md",
            },
          ],
          route: "route_document_verified",
          verification_result: {
            citation_valid: true,
            contradiction_count: 0,
            details: {},
            unsupported_claim_count: 0,
          },
          workspace_id: workspaceId,
        },
      });
      return;
    }

    throw new Error(`Unhandled E2E API request: ${method} ${url.pathname}`);
  });

  await page.goto("/");

  await expect(page.getByText("Use public demo documents only.")).toBeVisible();
  await expect(page.getByText("API healthy")).toBeVisible();

  await page.getByLabel("Workspace name").fill("Public decision record");
  await page.getByLabel("Workspace description").fill("Non-confidential source");
  await page.getByRole("button", { name: "Create workspace" }).click();

  await expect(page.getByRole("button", { name: "Public decision record" })).toBeVisible();

  await page.getByLabel("Upload document").setInputFiles({
    buffer: Buffer.from("# Approval\nThe rollout requires documented public evidence."),
    mimeType: "text/markdown",
    name: "public-evidence.md",
  });

  await expect(page.getByText("public-evidence.md")).toBeVisible();
  await expect(page.getByText("ready")).toBeVisible({ timeout: 5_000 });
  await expect(page.getByText("1 chunks")).toBeVisible();

  await page.getByRole("button", { name: "Verified Mode" }).click();
  await page
    .getByLabel("Question")
    .fill("What evidence supports the rollout decision?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("The rollout required cited public evidence [chunk-e2e].")).toBeVisible();
  await expect(
    page.getByText("The rollout requires documented public evidence before approval."),
  ).toBeVisible();
  await expect(page.getByRole("region", { name: "Retrieval trace" })).toContainText(
    "route_document_verified",
  );
  await expect(page.getByRole("region", { name: "Retrieval trace" })).toContainText(
    "hybrid #1",
  );
  await expect(page.getByRole("region", { name: "Retrieval trace" })).toContainText(
    "retrieval: 17 ms",
  );
});
