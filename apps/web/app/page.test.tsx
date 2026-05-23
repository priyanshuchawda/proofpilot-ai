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
  expect(screen.getByText("Gemini mode")).toBeInTheDocument();
  expect(screen.getByText("gemini-2.5-flash-lite only")).toBeInTheDocument();
  expect(screen.getByText("Free-tier mode")).toBeInTheDocument();
  expect(screen.getByText("Search grounding disabled by default")).toBeInTheDocument();
  expect(screen.getByText("Use public demo documents only.")).toBeInTheDocument();
});
