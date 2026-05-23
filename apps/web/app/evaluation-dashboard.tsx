"use client";

import { type EvaluationRunResponse, createProofPilotClient } from "@proofpilot/generated-api-client";
import { BarChart3, Loader2, Play } from "lucide-react";
import { useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function EvaluationDashboard() {
  const [run, setRun] = useState<EvaluationRunResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runEvaluation() {
    setIsLoading(true);
    setError(null);
    try {
      const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
      setRun(await apiClient.runEvaluation());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Evaluation failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="mt-5 rounded-lg border border-[#243247] bg-[#101827] p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#1d2332] text-[#67e8f9]">
            <BarChart3 aria-hidden="true" size={20} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Evaluation dashboard</h2>
            <p className="text-sm text-[#b8c7dd]">Deterministic checks</p>
          </div>
        </div>
        <button
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-[#67e8f9] px-3 font-semibold text-[#07111f] disabled:opacity-60"
          disabled={isLoading}
          onClick={runEvaluation}
          type="button"
        >
          {isLoading ? <Loader2 aria-hidden="true" className="animate-spin" size={17} /> : null}
          <Play aria-hidden="true" size={17} />
          Run Evaluation
        </button>
      </div>

      {error ? <p className="mt-4 text-sm text-[#fca5a5]">{error}</p> : null}
      {run ? (
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Dataset" value={`${run.summary.case_count} cases`} />
          <Metric label="Retrieval hit" value={formatRate(run.summary.retrieval_hit_rate)} />
          <Metric label="Citations" value={formatRate(run.summary.citation_validity_rate)} />
          <Metric label="Latency p95" value={`${run.summary.latency_p95_ms} ms`} />
          <Metric label="Refusals" value={formatRate(run.summary.refusal_correctness_rate)} />
          <Metric
            label="Contradictions"
            value={formatRate(run.summary.contradiction_correctness_rate)}
          />
          <Metric label="Cache hit" value={formatRate(run.summary.cache_hit_rate)} />
          <Metric label="Secret leaks" value={`${run.summary.secret_leak_count} leaks`} />
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[#2b3344] bg-[#0c1320] p-3">
      <p className="text-sm text-[#b8c7dd]">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function formatRate(value: number) {
  return `${Math.round(value * 100)}%`;
}
