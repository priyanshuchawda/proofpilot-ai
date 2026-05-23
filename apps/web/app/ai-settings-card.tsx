"use client";

import {
  createProofPilotClient,
  type AISettingsResponse,
} from "@proofpilot/generated-api-client";
import { Cpu, Search, SearchX, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

type SettingsState =
  | { status: "loading" }
  | { status: "ready"; settings: AISettingsResponse }
  | { status: "unavailable" };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function AISettingsCard() {
  const [state, setState] = useState<SettingsState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadSettings() {
      try {
        const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
        const settings = await apiClient.getAISettings();
        if (!cancelled) {
          setState({ settings, status: "ready" });
        }
      } catch {
        if (!cancelled) {
          setState({ status: "unavailable" });
        }
      }
    }

    void loadSettings();

    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "loading") {
    return <StaticSettings title="Loading Gemini settings" detail="Reading backend route config." />;
  }

  if (state.status === "unavailable") {
    return <StaticSettings title="Settings unavailable" detail="Start the backend to inspect models." />;
  }

  const settings = state.settings;
  const searchTitle = settings.search_grounding_enabled
    ? `Search via ${settings.search_grounding_model}`
    : "Search grounding disabled";
  const embeddingsTitle = settings.embeddings_enabled
    ? "Gemini embeddings enabled"
    : "Local embeddings active";

  return (
    <div className="mt-4 space-y-4">
      <StatusRow
        icon={<Cpu aria-hidden="true" size={20} />}
        label="Generation route"
        title={`${settings.generation_model} primary`}
        detail={`${settings.lightweight_model} lightweight`}
        tone="violet"
      />
      <StatusRow
        icon={
          settings.search_grounding_enabled ? (
            <Search aria-hidden="true" size={20} />
          ) : (
            <SearchX aria-hidden="true" size={20} />
          )
        }
        label="Gemini mode"
        title={searchTitle}
        detail={`Freshness model ${settings.freshness_model}`}
        tone="amber"
      />
      <StatusRow
        icon={<ShieldCheck aria-hidden="true" size={20} />}
        label="Embedding route"
        title={embeddingsTitle}
        detail={`${settings.embedding_model}, ${settings.embedding_dimension}d`}
        tone="cyan"
      />
    </div>
  );
}

function StaticSettings({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="mt-4">
      <StatusRow
        icon={<Cpu aria-hidden="true" size={20} />}
        label="Free-tier mode"
        title={title}
        detail={detail}
        tone="violet"
      />
    </div>
  );
}

function StatusRow({
  icon,
  label,
  title,
  detail,
  tone,
}: {
  icon: ReactNode;
  label: string;
  title: string;
  detail: string;
  tone: "amber" | "cyan" | "violet";
}) {
  const toneClasses = {
    amber: "text-[#fcd34d]",
    cyan: "text-[#67e8f9]",
    violet: "text-[#c4b5fd]",
  };

  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-[#2b3344] bg-[#0c1320] p-4">
      <div>
        <p className="text-sm font-medium text-[#b8c7dd]">{label}</p>
        <p className="mt-1 text-base font-semibold text-white">{title}</p>
        <p className="mt-1 text-sm text-[#b8c7dd]">{detail}</p>
      </div>
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-md bg-[#1d2332] ${toneClasses[tone]}`}
      >
        {icon}
      </div>
    </div>
  );
}
