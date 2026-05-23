import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { AISettingsCard } from "./ai-settings-card";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders backend Gemini model and embedding settings", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
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
        embeddings_enabled: true,
        search_grounding_enabled: true,
        live_smoke_enabled: false,
      }),
    }),
  );

  render(<AISettingsCard />);

  expect(screen.getByText("Loading Gemini settings")).toBeVisible();
  await waitFor(() => {
    expect(screen.getByText("gemini-3.1-flash-lite primary")).toBeVisible();
  });
  expect(screen.getByText("Search via gemini-2.5-flash-lite")).toBeVisible();
  expect(screen.getByText("Gemini embeddings enabled")).toBeVisible();
  expect(screen.getByText("gemini-embedding-2, 768d")).toBeVisible();
});

test("renders safe unavailable state without error internals", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("secret stack")));

  render(<AISettingsCard />);

  await waitFor(() => {
    expect(screen.getByText("Settings unavailable")).toBeVisible();
  });
  expect(screen.queryByText(/secret stack/)).not.toBeInTheDocument();
});
