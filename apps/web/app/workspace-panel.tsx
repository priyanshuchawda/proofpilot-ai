"use client";

import {
  createProofPilotClient,
  type DocumentResponse,
  type WorkspaceResponse,
} from "@proofpilot/generated-api-client";
import { FileUp, FolderPlus, RefreshCw } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function WorkspacePanel({
  onSelectWorkspace,
  selectedWorkspaceId,
}: {
  onSelectWorkspace: (workspaceId: string) => void;
  selectedWorkspaceId: string;
}) {
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadWorkspaces() {
      setIsLoadingWorkspaces(true);
      setError(null);
      try {
        const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
        const loaded = await apiClient.listWorkspaces();
        if (cancelled) {
          return;
        }
        setWorkspaces(loaded);
        if (!selectedWorkspaceId && loaded[0]) {
          onSelectWorkspace(loaded[0].id);
        }
      } catch {
        if (!cancelled) {
          setError("Workspace API unavailable.");
        }
      } finally {
        if (!cancelled) {
          setIsLoadingWorkspaces(false);
        }
      }
    }

    void loadWorkspaces();

    return () => {
      cancelled = true;
    };
  }, [onSelectWorkspace, selectedWorkspaceId]);

  useEffect(() => {
    let cancelled = false;
    async function loadDocuments() {
      if (!selectedWorkspaceId) {
        setDocuments([]);
        return;
      }
      setError(null);
      try {
        const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
        const loaded = await apiClient.listDocuments(selectedWorkspaceId);
        if (!cancelled) {
          setDocuments(loaded);
        }
      } catch {
        if (!cancelled) {
          setError("Document API unavailable.");
        }
      }
    }

    void loadDocuments();

    return () => {
      cancelled = true;
    };
  }, [selectedWorkspaceId]);

  async function createWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
      const workspace = await apiClient.createWorkspace({
        description: description.trim() || null,
        name: name.trim(),
      });
      setWorkspaces((current) => [workspace, ...current]);
      setName("");
      setDescription("");
      onSelectWorkspace(workspace.id);
    } catch {
      setError("Workspace creation failed.");
    }
  }

  async function uploadDocument(file: File | undefined) {
    if (!file || !selectedWorkspaceId) {
      return;
    }
    setIsUploading(true);
    setError(null);
    try {
      const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
      const document = await apiClient.uploadDocument(selectedWorkspaceId, file);
      setDocuments((current) => [document, ...current.filter((item) => item.id !== document.id)]);
    } catch {
      setError("Document upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section className="mt-10 grid gap-5 rounded-lg border border-[#243247] bg-[#101827] p-5 lg:grid-cols-[0.9fr_1.1fr]">
      <div>
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-white">Workspaces</h2>
          {isLoadingWorkspaces ? (
            <RefreshCw aria-hidden="true" className="animate-spin text-[#67e8f9]" size={18} />
          ) : null}
        </div>

        <form className="mt-4 grid gap-3" onSubmit={createWorkspace}>
          <label className="grid gap-2 text-sm font-medium text-[#c8d6ea]">
            Workspace name
            <input
              className="min-h-11 rounded-md border border-[#2b3344] bg-[#0c1320] px-3 text-base text-white outline-none focus:border-[#67e8f9]"
              onChange={(event) => setName(event.target.value)}
              required
              value={name}
            />
          </label>
          <label className="grid gap-2 text-sm font-medium text-[#c8d6ea]">
            Workspace description
            <input
              className="min-h-11 rounded-md border border-[#2b3344] bg-[#0c1320] px-3 text-base text-white outline-none focus:border-[#67e8f9]"
              onChange={(event) => setDescription(event.target.value)}
              value={description}
            />
          </label>
          <button
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-[#67e8f9] px-3 font-semibold text-[#07111f]"
            type="submit"
          >
            <FolderPlus aria-hidden="true" size={17} />
            Create workspace
          </button>
        </form>

        {error ? <p className="mt-4 text-sm text-[#fca5a5]">{error}</p> : null}

        <div className="mt-4 grid gap-2">
          {workspaces.length === 0 && !isLoadingWorkspaces ? (
            <p className="rounded-md border border-[#2b3344] bg-[#0c1320] p-3 text-sm text-[#b8c7dd]">
              No workspaces yet
            </p>
          ) : null}
          {workspaces.map((workspace) => (
            <button
              aria-label={workspace.name}
              className={`rounded-md border p-3 text-left ${
                selectedWorkspaceId === workspace.id
                  ? "border-[#67e8f9] bg-[#12323a]"
                  : "border-[#2b3344] bg-[#0c1320]"
              }`}
              key={workspace.id}
              onClick={() => onSelectWorkspace(workspace.id)}
              type="button"
            >
              <span className="block font-semibold text-white">{workspace.name}</span>
              <span className="mt-1 block text-xs text-[#b8c7dd]">{workspace.id}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-white">Documents</h2>
          <span className="rounded-md border border-[#2b3344] px-2 py-1 text-xs text-[#b8c7dd]">
            {selectedWorkspaceId || "Select workspace"}
          </span>
        </div>

        <label className="mt-4 flex min-h-28 cursor-pointer flex-col items-center justify-center gap-3 rounded-md border border-dashed border-[#2b3344] bg-[#0c1320] p-5 text-center text-sm text-[#b8c7dd]">
          <FileUp aria-hidden="true" className="text-[#67e8f9]" size={24} />
          <span>{isUploading ? "Uploading..." : "Upload PDF, TXT, or Markdown"}</span>
          <input
            accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
            aria-label="Upload document"
            className="sr-only"
            disabled={!selectedWorkspaceId || isUploading}
            onChange={(event) => {
              void uploadDocument(event.target.files?.[0]);
              event.target.value = "";
            }}
            type="file"
          />
        </label>

        <div className="mt-4 grid gap-2">
          {documents.length === 0 ? (
            <p className="rounded-md border border-[#2b3344] bg-[#0c1320] p-3 text-sm text-[#b8c7dd]">
              No documents indexed for this workspace.
            </p>
          ) : null}
          {documents.map((document) => (
            <article
              className="rounded-md border border-[#2b3344] bg-[#0c1320] p-3"
              key={document.id}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-white">{document.filename}</p>
                <span className="rounded-md border border-[#2b3344] px-2 py-1 text-xs text-[#b8c7dd]">
                  {document.status}
                </span>
              </div>
              <p className="mt-2 text-sm text-[#b8c7dd]">{document.chunk_count} chunks</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
