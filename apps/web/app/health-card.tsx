"use client";

import { createProofPilotClient, type HealthResponse } from "@proofpilot/generated-api-client";
import { Activity } from "lucide-react";
import { useEffect, useState } from "react";

type HealthState =
  | { status: "checking" }
  | { status: "healthy"; health: HealthResponse }
  | { status: "unavailable" };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function HealthCard() {
  const [healthState, setHealthState] = useState<HealthState>({ status: "checking" });

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
        const health = await apiClient.getHealth();
        if (!cancelled) {
          setHealthState({ health, status: "healthy" });
        }
      } catch {
        if (!cancelled) {
          setHealthState({ status: "unavailable" });
        }
      }
    }

    void checkHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  const title =
    healthState.status === "checking"
      ? "Checking API"
      : healthState.status === "healthy"
        ? "API healthy"
        : "API unavailable";
  const detail =
    healthState.status === "healthy"
      ? `${healthState.health.service} v${healthState.health.version}`
      : healthState.status === "checking"
        ? "Contacting backend on port 8000."
        : "Start the backend on port 8000.";

  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-[#b8c7dd]">API health</p>
        <p className="mt-2 text-2xl font-semibold text-white">{title}</p>
        <p className="mt-1 text-sm text-[#b8c7dd]">{detail}</p>
      </div>
      <div className="flex h-11 w-11 items-center justify-center rounded-md bg-[#12323a] text-[#67e8f9]">
        <Activity aria-hidden="true" size={22} />
      </div>
    </div>
  );
}
