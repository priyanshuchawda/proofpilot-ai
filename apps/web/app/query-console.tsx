"use client";

import {
  createProofPilotClient,
  type AnswerResponse,
  type Citation,
  type QueryRunTraceResponse,
} from "@proofpilot/generated-api-client";
import { FileText, Globe2, Loader2, Send } from "lucide-react";
import { FormEvent, useState } from "react";

type Mode = "fast" | "verified";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function QueryConsole({ workspaceId }: { workspaceId?: string }) {
  const [workspaceInput, setWorkspaceInput] = useState("");
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>("fast");
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [queryRunTrace, setQueryRunTrace] = useState<QueryRunTraceResponse | null>(null);
  const [streamedText, setStreamedText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const effectiveWorkspaceId = workspaceId || workspaceInput;

  async function loadQueryRunTrace(queryRunId: string) {
    setTraceError(null);
    try {
      const apiClient = createProofPilotClient({ baseUrl: apiBaseUrl });
      setQueryRunTrace(await apiClient.getQueryRun(queryRunId));
    } catch {
      setTraceError("Persisted trace details unavailable.");
    }
  }

  async function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setAnswer(null);
    setQueryRunTrace(null);
    setTraceError(null);
    setStreamedText("");

    try {
      await streamQueryWorkspace({
        mode,
        onDelta: (text) => {
          setStreamedText((current) => `${current}${text}`);
        },
        onFinal: (finalAnswer) => {
          setAnswer(finalAnswer);
          void loadQueryRunTrace(finalAnswer.query_run_id);
        },
        query: question,
        workspaceId: effectiveWorkspaceId,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Query failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="mt-10 grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
      <form
        aria-label="Ask documents"
        className="rounded-lg border border-[#243247] bg-[#101827] p-5"
        onSubmit={submitQuery}
      >
        <div className="grid gap-4">
          <label className="grid gap-2 text-sm font-medium text-[#c8d6ea]">
            Workspace ID
            <input
              className="min-h-11 rounded-md border border-[#2b3344] bg-[#0c1320] px-3 text-base text-white outline-none focus:border-[#67e8f9]"
              readOnly={Boolean(workspaceId)}
              onChange={(event) => setWorkspaceInput(event.target.value)}
              required
              value={effectiveWorkspaceId}
            />
          </label>

          <label className="grid gap-2 text-sm font-medium text-[#c8d6ea]">
            Question
            <textarea
              className="min-h-28 resize-none rounded-md border border-[#2b3344] bg-[#0c1320] px-3 py-3 text-base text-white outline-none focus:border-[#67e8f9]"
              onChange={(event) => setQuestion(event.target.value)}
              required
              value={question}
            />
          </label>

          <div className="flex flex-wrap gap-2" role="group" aria-label="Answer mode">
            {(["fast", "verified"] as const).map((option) => (
              <button
                className={`min-h-10 rounded-md border px-3 text-sm font-semibold ${
                  mode === option
                    ? "border-[#67e8f9] bg-[#12323a] text-[#e9fbff]"
                    : "border-[#2b3344] bg-[#0c1320] text-[#b8c7dd]"
                }`}
                key={option}
                onClick={() => setMode(option)}
                type="button"
              >
                {option === "fast" ? "Fast Mode" : "Verified Mode"}
              </button>
            ))}
          </div>

          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-[#67e8f9] px-4 font-semibold text-[#07111f] disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isLoading}
            type="submit"
          >
            {isLoading ? <Loader2 aria-hidden="true" className="animate-spin" size={18} /> : null}
            <Send aria-hidden="true" size={18} />
            Ask
          </button>
        </div>
      </form>

      <div className="rounded-lg border border-[#243247] bg-[#101827] p-5">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-white">Cited answer</h2>
          <span className="rounded-md border border-[#2b3344] px-2 py-1 text-xs text-[#b8c7dd]">
            {answer?.route ?? mode}
          </span>
        </div>

        {error ? <p className="mt-4 text-sm text-[#fca5a5]">{error}</p> : null}
        {isLoading ? <p className="mt-4 text-sm text-[#b8c7dd]">Streaming response...</p> : null}
        {streamedText && !answer ? (
          <p className="mt-4 text-base leading-7 text-[#eef4ff]">{streamedText}</p>
        ) : null}
        {answer ? (
          <div className="mt-4 space-y-4">
            {answer.refusal_reason ? (
              <p className="text-base leading-7 text-[#fcd7a3]">{answer.refusal_reason}</p>
            ) : (
              <p className="text-base leading-7 text-[#eef4ff]">{answer.answer_text}</p>
            )}

            <div className="flex flex-wrap gap-2">
              <span className="rounded-md border border-[#2b3344] px-2 py-1 text-sm text-[#c8d6ea]">
                {answer.freshness_label}
              </span>
              {answer.citations.map((citation) => (
                <span
                  className="inline-flex items-center gap-2 rounded-md border border-[#2b3344] bg-[#0c1320] px-2 py-1 text-sm text-[#c8d6ea]"
                  key={citationLabel(citation)}
                >
                  {citation.source_kind === "web" ? (
                    <Globe2 aria-hidden="true" size={15} />
                  ) : (
                    <FileText aria-hidden="true" size={15} />
                  )}
                  {citationLabel(citation)}
                </span>
              ))}
            </div>

            {(answer.contradictions ?? []).length > 0 ? (
              <div className="rounded-md border border-[#5b3b2b] bg-[#22140d] p-3 text-sm text-[#fcd7a3]">
                Conflicts found:{" "}
                {(answer.contradictions ?? [])
                  .map((contradiction) => contradiction.claim_key)
                  .join(", ")}
              </div>
            ) : null}

            <RetrievalTrace answer={answer} queryRunTrace={queryRunTrace} traceError={traceError} />

            <div className="space-y-3">
              {answer.citations.map((citation) => (
                <EvidenceCard citation={citation} key={`${citationLabel(citation)}-evidence`} />
              ))}
            </div>

            {answer.search_suggestions_html ? (
              <section aria-label="Google Search suggestions" className="space-y-2">
                <h3 className="text-xs font-semibold uppercase text-[#8ea4c2]">
                  Google Search suggestions
                </h3>
                <iframe
                  className="h-14 w-full rounded-md border border-[#2b3344] bg-white"
                  sandbox="allow-popups"
                  srcDoc={answer.search_suggestions_html}
                  title="Google Search suggestions"
                />
              </section>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function RetrievalTrace({
  answer,
  queryRunTrace,
  traceError,
}: {
  answer: AnswerResponse;
  queryRunTrace: QueryRunTraceResponse | null;
  traceError: string | null;
}) {
  const evidenceChunkIds = answer.evidence_chunk_ids.length
    ? answer.evidence_chunk_ids.join(", ")
    : "none";
  const citedChunkIds = answer.citations.length
    ? answer.citations.map((citation) => citationLabel(citation)).join(", ")
    : "none";
  const contradictionKeys = (answer.contradictions ?? []).length
    ? (answer.contradictions ?? []).map((contradiction) => contradiction.claim_key).join(", ")
    : "none";

  return (
    <section
      aria-label="Retrieval trace"
      className="rounded-md border border-[#2b3344] bg-[#0c1320] p-3"
      role="region"
    >
      <h3 className="text-sm font-semibold text-white">Retrieval trace</h3>
      <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
        <TraceItem label="Route" value={answer.route} />
        <TraceItem label="Cache" value={answer.cache_status ?? "unknown"} />
        <TraceItem label="Confidence" value={answer.confidence_label} />
        <TraceItem label="Freshness" value={answer.freshness_label} />
        <TraceItem label="Live grounding" value={answer.live_grounding_used ? "used" : "not used"} />
        <TraceItem label="Query run" value={answer.query_run_id} />
        <TraceItem label="Evidence chunks" value={evidenceChunkIds} />
        <TraceItem label="Cited chunks" value={citedChunkIds} />
        <TraceItem label="Contradictions" value={contradictionKeys} />
      </dl>
      {traceError ? <p className="mt-3 text-sm text-[#fca5a5]">{traceError}</p> : null}
      {queryRunTrace ? (
        <div className="mt-4 grid gap-4">
          <div>
            <h4 className="text-xs font-semibold uppercase text-[#8ea4c2]">
              Retrieved candidates
            </h4>
            {queryRunTrace.retrieval_candidates.length ? (
              <ul className="mt-2 grid gap-2">
                {queryRunTrace.retrieval_candidates.map((candidate) => (
                  <li
                    className="rounded-md border border-[#243247] p-2 text-sm text-[#dbe8f7]"
                    key={`${candidate.source}-${candidate.rank}-${candidate.chunk_id}`}
                  >
                    <span className="font-semibold text-white">
                      {candidate.source} #{candidate.rank}
                    </span>
                    <span className="ml-2">{candidate.source_filename ?? candidate.chunk_id}</span>
                    <span className="ml-2 text-[#8ea4c2]">score {candidate.score}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-[#8ea4c2]">No persisted candidates.</p>
            )}
          </div>

          {queryRunTrace.latency_metrics.length ? (
            <div>
              <h4 className="text-xs font-semibold uppercase text-[#8ea4c2]">Latency</h4>
              <div className="mt-2 flex flex-wrap gap-2">
                {queryRunTrace.latency_metrics.map((metric) => (
                  <span
                    className="rounded-md border border-[#243247] px-2 py-1 text-sm text-[#dbe8f7]"
                    key={`${metric.metric_name}-${metric.duration_ms}`}
                  >
                    {metric.metric_name}: {metric.duration_ms} ms
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function EvidenceCard({ citation }: { citation: Citation }) {
  if (citation.source_kind === "web") {
    return (
      <article className="rounded-md border border-[#2b3344] bg-[#0c1320] p-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-[#b8c7dd]">
          <span className="rounded-md border border-[#214a38] bg-[#10251d] px-2 py-1 text-xs font-semibold text-[#b6f3d2]">
            Live web source
          </span>
          <span className="text-[#8ea4c2]">{citationLabel(citation)}</span>
        </div>
        {citation.uri ? (
          <a
            className="mt-2 inline-block break-words text-sm font-semibold text-[#67e8f9] underline-offset-4 hover:underline"
            href={citation.uri}
            rel="noreferrer"
            target="_blank"
          >
            {citation.title ?? citation.source_filename ?? citation.uri}
          </a>
        ) : (
          <p className="mt-2 text-sm font-semibold text-white">
            {citation.title ?? citation.source_filename ?? "Web source"}
          </p>
        )}
        <p className="mt-2 text-sm leading-6 text-[#c8d6ea]">{citation.evidence_text}</p>
      </article>
    );
  }

  return (
    <article className="rounded-md border border-[#2b3344] bg-[#0c1320] p-3">
      <div className="flex flex-wrap items-center gap-2 text-sm text-[#b8c7dd]">
        <span className="font-semibold text-white">{citation.source_filename}</span>
        {citation.section_heading ? <span>{citation.section_heading}</span> : null}
        {citation.page_number ? <span>Page {citation.page_number}</span> : null}
      </div>
      <p className="mt-2 text-sm leading-6 text-[#c8d6ea]">{citation.evidence_text}</p>
    </article>
  );
}

function citationLabel(citation: Citation) {
  return citation.citation_label ?? citation.chunk_id ?? "source";
}

function TraceItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase text-[#8ea4c2]">{label}</dt>
      <dd className="mt-1 break-words text-[#dbe8f7]">{value}</dd>
    </div>
  );
}

async function streamQueryWorkspace({
  mode,
  onDelta,
  onFinal,
  query,
  workspaceId,
}: {
  mode: Mode;
  onDelta: (text: string) => void;
  onFinal: (answer: AnswerResponse) => void;
  query: string;
  workspaceId: string;
}) {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/workspaces/${encodeURIComponent(workspaceId)}/query/stream`,
    {
      body: JSON.stringify({ query, mode }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    },
  );

  if (!response.ok) {
    throw new Error("Query failed. Check the workspace and backend status.");
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    buffer = processSseBuffer(buffer, onDelta, onFinal);
    if (done) {
      break;
    }
  }
}

function processSseBuffer(
  buffer: string,
  onDelta: (text: string) => void,
  onFinal: (answer: AnswerResponse) => void,
) {
  const events = buffer.split("\n\n");
  const remainder = events.pop() ?? "";

  for (const eventBlock of events) {
    const event = parseSseEvent(eventBlock);
    if (!event) {
      continue;
    }
    if (event.type === "answer_delta") {
      const payload = JSON.parse(event.data) as { text: string };
      onDelta(payload.text);
    }
    if (event.type === "final") {
      onFinal(JSON.parse(event.data) as AnswerResponse);
    }
  }

  return remainder;
}

function parseSseEvent(eventBlock: string) {
  const eventLine = eventBlock.split("\n").find((line) => line.startsWith("event: "));
  const dataLine = eventBlock.split("\n").find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) {
    return null;
  }

  return {
    data: dataLine.slice("data: ".length),
    type: eventLine.slice("event: ".length),
  };
}
