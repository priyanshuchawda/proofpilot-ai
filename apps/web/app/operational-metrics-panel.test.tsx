import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { OperationalMetricsPanel } from "./operational-metrics-panel";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders privacy-safe operational metrics from the backend", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        dependencies: [
          { detail: null, name: "postgres", status: "ok" },
          { detail: "ConnectionError", name: "redis", status: "error" },
        ],
        telemetry: {
          cache_events: [
            {
              cache_name: "response",
              count: 3,
              mode: "fast",
              result: "hit",
              workspace_hash: "abc123def4567890",
            },
            {
              cache_name: "response",
              count: 1,
              mode: "verified",
              result: "miss",
              workspace_hash: "fedcba0987654321",
            },
          ],
          gemini_errors: [
            {
              count: 2,
              model: "gemini-2.5-flash-lite",
              provider: "google-genai",
              status_code: 429,
            },
          ],
          gemini_requests: [
            {
              count: 5,
              google_search: false,
              model: "gemini-2.5-flash-lite",
              provider: "google-genai",
            },
          ],
        },
      }),
    }),
  );

  render(<OperationalMetricsPanel />);

  expect(screen.getByText("Operational metrics")).toBeVisible();
  await waitFor(() => {
    expect(screen.getByText("postgres ok")).toBeVisible();
  });
  expect(screen.getByText("redis error")).toBeVisible();
  expect(screen.getByText("Gemini requests")).toBeVisible();
  expect(screen.getByText("google-genai · gemini-2.5-flash-lite · no Search")).toBeVisible();
  expect(screen.getByText("Gemini errors")).toBeVisible();
  expect(screen.getByText("google-genai · gemini-2.5-flash-lite · HTTP 429")).toBeVisible();
  expect(screen.getByText("Cache events")).toBeVisible();
  expect(screen.getByText("response · fast · hit")).toBeVisible();
  expect(screen.getByText("response · verified · miss")).toBeVisible();
  expect(screen.queryByText(/workspace-a|What is the policy|AIza/)).not.toBeInTheDocument();
});

test("renders safe unavailable state without backend error internals", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("secret stack")));

  render(<OperationalMetricsPanel />);

  await waitFor(() => {
    expect(screen.getByText("Metrics unavailable")).toBeVisible();
  });
  expect(screen.queryByText(/secret stack/)).not.toBeInTheDocument();
});
