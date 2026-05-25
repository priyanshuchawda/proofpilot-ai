"use client";

import {
  type CacheEventMetric,
  createProofPilotClient,
  type GeminiErrorMetric,
  type GeminiRequestMetric,
  type OperationalMetricsResponse,
} from "@proofpilot/generated-api-client";
import { Activity, AlertTriangle, Database, Loader2, Server } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type MetricsState =
  | { status: "loading" }
  | { status: "ready"; metrics: OperationalMetricsResponse }
  | { status: "unavailable" };

export function OperationalMetricsPanel() {
  const [state, setState] = useState<MetricsState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadMetrics() {
      try {
        const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
        const metrics = await apiClient.getOperationalMetrics();
        if (!cancelled) {
          setState({ metrics, status: "ready" });
        }
      } catch {
        if (!cancelled) {
          setState({ status: "unavailable" });
        }
      }
    }

    void loadMetrics();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="mt-5 rounded-lg border border-[#243247] bg-[#101827] p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#1d2332] text-[#67e8f9]">
          <Activity aria-hidden="true" size={20} />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">Operational metrics</h2>
          <p className="text-sm text-[#b8c7dd]">Local aggregate telemetry</p>
        </div>
      </div>

      {state.status === "loading" ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-[#b8c7dd]">
          <Loader2 aria-hidden="true" className="animate-spin" size={16} />
          Loading metrics
        </div>
      ) : null}

      {state.status === "unavailable" ? (
        <p className="mt-4 text-sm text-[#fca5a5]">Metrics unavailable</p>
      ) : null}

      {state.status === "ready" ? <MetricsBody metrics={state.metrics} /> : null}
    </section>
  );
}

function MetricsBody({ metrics }: { metrics: OperationalMetricsResponse }) {
  return (
    <div className="mt-5 grid gap-4 lg:grid-cols-2">
      <MetricGroup
        icon={<Server aria-hidden="true" size={18} />}
        title="Dependencies"
        empty="No dependency health reported."
      >
        {metrics.dependencies.map((dependency) => (
          <MetricRow
            key={dependency.name}
            label={`${dependency.name} ${dependency.status}`}
            value={dependency.detail ?? "available"}
            tone={dependency.status === "ok" ? "good" : "warn"}
          />
        ))}
      </MetricGroup>

      <MetricGroup
        icon={<Database aria-hidden="true" size={18} />}
        title="Cache events"
        empty="No cache activity recorded."
      >
        {metrics.telemetry.cache_events.map((event) => (
          <MetricRow
            key={`${event.cache_name}-${event.mode}-${event.result}-${event.workspace_hash}`}
            label={cacheEventLabel(event)}
            value={`${event.count} events · workspace ${event.workspace_hash}`}
            tone={event.result === "hit" ? "good" : "neutral"}
          />
        ))}
      </MetricGroup>

      <MetricGroup
        icon={<Activity aria-hidden="true" size={18} />}
        title="Gemini requests"
        empty="No Gemini calls recorded."
      >
        {metrics.telemetry.gemini_requests.map((request) => (
          <MetricRow
            key={`${request.provider}-${request.model}-${request.google_search}`}
            label={geminiRequestLabel(request)}
            value={`${request.count} calls`}
            tone="neutral"
          />
        ))}
      </MetricGroup>

      <MetricGroup
        icon={<AlertTriangle aria-hidden="true" size={18} />}
        title="Gemini errors"
        empty="No provider errors recorded."
      >
        {metrics.telemetry.gemini_errors.map((error) => (
          <MetricRow
            key={`${error.provider}-${error.model}-${error.status_code ?? "unknown"}`}
            label={geminiErrorLabel(error)}
            value={`${error.count} errors`}
            tone="warn"
          />
        ))}
      </MetricGroup>
    </div>
  );
}

function MetricGroup({
  children,
  empty,
  icon,
  title,
}: {
  children: ReactNode;
  empty: string;
  icon: ReactNode;
  title: string;
}) {
  const rows = Array.isArray(children) ? children.filter(Boolean) : children;
  const isEmpty = Array.isArray(rows) ? rows.length === 0 : !rows;

  return (
    <div className="rounded-md border border-[#2b3344] bg-[#0c1320] p-4">
      <div className="flex items-center gap-2 text-[#67e8f9]">
        {icon}
        <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-[#b8c7dd]">
          {title}
        </h3>
      </div>
      <div className="mt-3 space-y-2">
        {isEmpty ? <p className="text-sm text-[#7f8ea3]">{empty}</p> : rows}
      </div>
    </div>
  );
}

function MetricRow({
  label,
  tone,
  value,
}: {
  label: string;
  tone: "good" | "neutral" | "warn";
  value: string;
}) {
  const toneClass = {
    good: "text-[#86efac]",
    neutral: "text-[#bfdbfe]",
    warn: "text-[#fcd34d]",
  }[tone];

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-[#121b2b] px-3 py-2">
      <p className="text-sm font-medium text-white">{label}</p>
      <p className={`text-sm ${toneClass}`}>{value}</p>
    </div>
  );
}

function cacheEventLabel(event: CacheEventMetric) {
  return `${event.cache_name} · ${event.mode} · ${event.result}`;
}

function geminiRequestLabel(request: GeminiRequestMetric) {
  return `${request.provider} · ${request.model} · ${request.google_search ? "Search" : "no Search"}`;
}

function geminiErrorLabel(error: GeminiErrorMetric) {
  return `${error.provider} · ${error.model} · ${
    error.status_code === null ? "unknown status" : `HTTP ${error.status_code}`
  }`;
}
