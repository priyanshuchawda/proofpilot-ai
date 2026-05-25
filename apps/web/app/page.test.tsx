import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import Home from "./page";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders the API health check status", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return {
          ok: true,
          json: async () => ({
            service: "proofpilot-api",
            status: "ok",
            version: "0.1.0",
          }),
        };
      }
      if (url.endsWith("/api/v1/settings/ai")) {
        return {
          ok: true,
          json: async () => ({
            backend_only: true,
            gemini_configured: true,
            generation_model: "gemini-3.1-flash-lite",
            lightweight_model: "gemini-2.5-flash-lite",
            freshness_model: "gemini-3.1-flash-lite",
            search_grounding_model: "gemini-2.5-flash-lite",
            embedding_model: "gemini-embedding-2",
            embedding_dimension: 768,
            embeddings_enabled: false,
            search_grounding_enabled: false,
            live_smoke_enabled: false,
          }),
        };
      }
      if (url.endsWith("/api/v1/metrics/operational")) {
        return {
          ok: true,
          json: async () => ({
            dependencies: [{ detail: null, name: "postgres", status: "ok" }],
            telemetry: {
              cache_events: [],
              gemini_errors: [],
              gemini_requests: [],
            },
          }),
        };
      }

      return {
        ok: true,
        json: async () => [],
      };
    }),
  );
  render(<Home />);

  expect(screen.getByRole("heading", { name: "ProofPilot AI" })).toBeInTheDocument();
  expect(screen.getByText("API health")).toBeInTheDocument();
  expect(screen.getByText("Checking API")).toBeInTheDocument();
  await waitFor(() => {
    expect(screen.getByText("API healthy")).toBeInTheDocument();
  });
  await waitFor(() => {
    expect(screen.getByText("gemini-3.1-flash-lite primary")).toBeInTheDocument();
  });
  expect(screen.getByText("Gemini mode")).toBeInTheDocument();
  expect(screen.getByText("Generation route")).toBeInTheDocument();
  expect(screen.getByText("Search grounding disabled")).toBeInTheDocument();
  expect(screen.getByText("Local embeddings active")).toBeInTheDocument();
  expect(screen.getByText("Use public demo documents only.")).toBeInTheDocument();
});
