import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { EvaluationDashboard } from "./evaluation-dashboard";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("runs evaluation and renders deterministic metrics", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      run_id: "run-a",
      status: "completed",
      summary: {
        case_count: 6,
        retrieval_hit_rate: 0.83,
        citation_validity_rate: 1,
        refusal_correctness_rate: 1,
        contradiction_correctness_rate: 1,
        latency_p50_ms: 120,
        latency_p95_ms: 150,
        cache_hit_rate: 0.33,
        secret_leak_count: 0,
      },
    }),
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<EvaluationDashboard />);

  fireEvent.click(screen.getByRole("button", { name: "Run Evaluation" }));

  await waitFor(() => {
    expect(screen.getByText("6 cases")).toBeVisible();
  });
  expect(screen.getByText("Deterministic checks")).toBeVisible();
  expect(screen.getByText("0 leaks")).toBeVisible();
});
