import { Cpu, SearchX, ShieldCheck } from "lucide-react";

import { DashboardWorkflow } from "./dashboard-workflow";
import { HealthCard } from "./health-card";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0a0f1a] text-[#eef4ff]">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-6 py-12">
        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div className="space-y-6">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#67e8f9]">
              Evidence-first GenAI
            </p>
            <div className="space-y-4">
              <h1 className="text-4xl font-semibold tracking-normal text-white md:text-6xl">
                ProofPilot AI
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-[#b8c7dd]">
                A decision copilot for grounded answers, precise citations, retrieval traces,
                privacy-first uploads, and measurable evaluation.
              </p>
            </div>
          </div>

          <aside className="rounded-lg border border-[#243247] bg-[#101827] p-5 shadow-2xl shadow-black/20">
            <HealthCard />

            <div className="mt-4 flex items-center justify-between gap-4 rounded-md border border-[#2b3344] bg-[#0c1320] p-4">
              <div>
                <p className="text-sm font-medium text-[#b8c7dd]">Free-tier mode</p>
                <p className="mt-1 text-base font-semibold text-white">
                  gemini-2.5-flash-lite only
                </p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#1d2332] text-[#c4b5fd]">
                <Cpu aria-hidden="true" size={20} />
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between gap-4 rounded-md border border-[#2b3344] bg-[#0c1320] p-4">
              <div>
                <p className="text-sm font-medium text-[#b8c7dd]">Gemini mode</p>
                <p className="mt-1 text-base font-semibold text-white">
                  Search grounding disabled by default
                </p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#1d2332] text-[#fcd34d]">
                <SearchX aria-hidden="true" size={20} />
              </div>
            </div>

            <div className="mt-6 flex items-start gap-3 rounded-md border border-[#1f3b36] bg-[#0d211f] p-4 text-sm leading-6 text-[#b7f7dd]">
              <ShieldCheck aria-hidden="true" className="mt-0.5 shrink-0" size={18} />
              <p>
                <span>Gemini keys stay server-side.</span>{" "}
                <span>Use public demo documents only.</span>{" "}
                <span>
                  Do not upload secrets, credentials, private keys, or confidential files.
                </span>
              </p>
            </div>
          </aside>
        </div>

        <DashboardWorkflow />
      </section>
    </main>
  );
}
