import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { HealthCard } from "./health-card";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders healthy API status from the backend health endpoint", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        service: "proofpilot-api",
        status: "ok",
        version: "0.1.0",
      }),
    }),
  );

  render(<HealthCard />);

  expect(screen.getByText("Checking API")).toBeVisible();
  await waitFor(() => {
    expect(screen.getByText("API healthy")).toBeVisible();
  });
  expect(screen.getByText("proofpilot-api v0.1.0")).toBeVisible();
});

test("renders unavailable API status without leaking error internals", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED 127.0.0.1:8000")),
  );

  render(<HealthCard />);

  await waitFor(() => {
    expect(screen.getByText("API unavailable")).toBeVisible();
  });
  expect(screen.getByText("Start the backend on port 8000.")).toBeVisible();
  expect(screen.queryByText(/ECONNREFUSED/)).not.toBeInTheDocument();
});
