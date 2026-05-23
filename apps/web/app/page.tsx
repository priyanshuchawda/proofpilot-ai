import { ShieldCheck } from "lucide-react";

import { AISettingsCard } from "./ai-settings-card";
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
            <AISettingsCard />

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
