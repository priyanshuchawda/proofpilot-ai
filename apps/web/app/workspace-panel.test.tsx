import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { WorkspacePanel } from "./workspace-panel";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("creates and selects a workspace from backend data", async () => {
  const onSelectWorkspace = vi.fn();
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        description: "Demo sources",
        id: "workspace-demo",
        name: "Demo Workspace",
      }),
    });
  vi.stubGlobal("fetch", fetchMock);

  render(<WorkspacePanel onSelectWorkspace={onSelectWorkspace} selectedWorkspaceId="" />);

  await waitFor(() => {
    expect(screen.getByText("No workspaces yet")).toBeVisible();
  });

  fireEvent.change(screen.getByLabelText("Workspace name"), {
    target: { value: "Demo Workspace" },
  });
  fireEvent.change(screen.getByLabelText("Workspace description"), {
    target: { value: "Demo sources" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));

  await waitFor(() => {
    expect(onSelectWorkspace).toHaveBeenCalledWith("workspace-demo");
  });
  expect(screen.getByRole("button", { name: "Demo Workspace" })).toBeVisible();
});

test("lists documents and uploads a file for the selected workspace", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          description: null,
          id: "workspace-demo",
          name: "Demo Workspace",
        },
      ],
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          chunk_count: 3,
          filename: "policy.md",
          id: "doc-a",
          mime_type: "text/markdown",
          status: "ready",
          workspace_id: "workspace-demo",
        },
      ],
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        chunk_count: 0,
        filename: "notes.txt",
        id: "doc-b",
        mime_type: "text/plain",
        status: "uploaded",
        workspace_id: "workspace-demo",
      }),
    });
  vi.stubGlobal("fetch", fetchMock);

  render(
    <WorkspacePanel
      onSelectWorkspace={vi.fn()}
      selectedWorkspaceId="workspace-demo"
    />,
  );

  await waitFor(() => {
    expect(screen.getByText("policy.md")).toBeVisible();
  });

  const file = new File(["hello"], "notes.txt", { type: "text/plain" });
  fireEvent.change(screen.getByLabelText("Upload document"), {
    target: { files: [file] },
  });

  await waitFor(() => {
    expect(screen.getByText("notes.txt")).toBeVisible();
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/api/v1/workspaces/workspace-demo/documents",
    expect.objectContaining({ method: "POST" }),
  );
});

test("polls active document processing until the document is ready", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          description: null,
          id: "workspace-demo",
          name: "Demo Workspace",
        },
      ],
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          chunk_count: 0,
          filename: "processing.md",
          id: "doc-processing",
          mime_type: "text/markdown",
          status: "uploaded",
          workspace_id: "workspace-demo",
        },
      ],
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          chunk_count: 2,
          filename: "processing.md",
          id: "doc-processing",
          mime_type: "text/markdown",
          status: "ready",
          workspace_id: "workspace-demo",
        },
      ],
    });
  vi.stubGlobal("fetch", fetchMock);

  render(
    <WorkspacePanel
      onSelectWorkspace={vi.fn()}
      selectedWorkspaceId="workspace-demo"
    />,
  );

  await waitFor(() => {
    expect(screen.getByText("uploaded")).toBeVisible();
  });

  await waitFor(
    () => {
      expect(screen.getByText("ready")).toBeVisible();
      expect(screen.getByText("2 chunks")).toBeVisible();
    },
    { timeout: 2500 },
  );
});

test("shows a safe message when document processing fails", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          description: null,
          id: "workspace-demo",
          name: "Demo Workspace",
        },
      ],
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          chunk_count: 0,
          filename: "failed.md",
          id: "doc-failed",
          mime_type: "text/markdown",
          status: "failed",
          workspace_id: "workspace-demo",
        },
      ],
    });
  vi.stubGlobal("fetch", fetchMock);

  render(
    <WorkspacePanel
      onSelectWorkspace={vi.fn()}
      selectedWorkspaceId="workspace-demo"
    />,
  );

  await waitFor(() => {
    expect(screen.getByText("failed")).toBeVisible();
    expect(screen.getByText("Processing failed. Retry with a supported public document.")).toBeVisible();
  });
});
