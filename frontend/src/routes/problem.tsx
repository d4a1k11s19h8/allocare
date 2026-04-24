import { PageLayout, PageHeader } from "@/components/PageLayout";

const USERS = [
  {
    role: "NGO Coordinator",
    pain: "Spends 4–6 hrs/week analyzing paper surveys and assigning volunteers via phone.",
    fix: "Dashboard auto-scores urgency; top-3 matched volunteers suggested per need in <10 seconds.",
  },
  {
    role: "Field Volunteer",
    pain: "Doesn't know where their effort matters most; feels disconnected from impact.",
    fix: "Task feed ranked by urgency + impact framing: 'This helps 47 families with food insecurity.'",
  },
  {
    role: "Field Data Collector",
    pain: "Paper surveys never make it into any digital system for analysis or action.",
    fix: "Photo of paper form → Cloud Vision OCR → structured urgency record in <30 seconds.",
  },
  {
    role: "NGO Leadership",
    pain: "Cannot see cross-area patterns; duplicate efforts across branches and partner orgs.",
    fix: "District heatmap + trend analytics show where needs are rising vs. resolved over time.",
  },
];

export default function ProblemPage() {
  return (
    <PageLayout>
      <PageHeader
        eyebrow="The Problem"
        title="It's not lack of resources. It's misallocation due to poor visibility."
        intro="Local NGOs collect valuable need-data through paper surveys, WhatsApp messages, and field reports. That data sits in physical files, disconnected spreadsheets, or one coordinator's memory."
      />

      <section className="mx-auto max-w-5xl px-6 py-16">
        <div className="rounded-2xl border-l-4 border-[#E02424] bg-red-50/60 p-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-[#E02424]">Critical distinction</h3>
          <p className="mt-3 text-lg text-slate-800">
            Most teams will build a generic volunteer listing platform. That fails the brief. The solution must create
            <span className="font-semibold"> visibility, intelligence, and automated routing</span> — not a bulletin board.
          </p>
        </div>

        <h2 className="mt-16 text-2xl font-bold text-slate-900">Three compounding failures</h2>
        <div className="mt-6 space-y-4">
          {[
            { t: "Data is undigitized", b: "Paper surveys and handwritten field reports cannot be analyzed at scale. Seasonal hunger spikes and recurring flood areas stay invisible." },
            { t: "Data is siloed", b: "Even when digitized, need-data lives across WhatsApp threads, individual Google Sheets, and email chains. No unified view to compare urgency across areas or organizations." },
            { t: "Matching is manual", b: "Volunteer coordinators assign tasks through personal knowledge and phone calls. Slow, non-scalable, language-limited, and systematically misses best-fit assignments." },
          ].map((x, i) => (
            <div key={x.t} className="flex gap-4 rounded-xl border border-slate-200 bg-white p-5">
              <div className="grid h-9 w-9 flex-none place-items-center rounded-lg bg-slate-900 text-sm font-bold text-white">{i + 1}</div>
              <div>
                <h3 className="font-semibold text-slate-900">{x.t}</h3>
                <p className="mt-1 text-sm text-slate-600">{x.b}</p>
              </div>
            </div>
          ))}
        </div>

        <h2 className="mt-16 text-2xl font-bold text-slate-900">Who feels this pain</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {USERS.map((u) => (
            <div key={u.role} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-[#1A56DB]">{u.role}</div>
              <div className="mt-3 text-sm text-slate-700"><span className="font-semibold text-slate-900">Pain:</span> {u.pain}</div>
              <div className="mt-2 text-sm text-slate-700"><span className="font-semibold text-[#0E9F6E]">AlloCare fix:</span> {u.fix}</div>
            </div>
          ))}
        </div>
      </section>
    </PageLayout>
  );
}
