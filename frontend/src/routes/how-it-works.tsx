import { PageLayout, PageHeader } from "@/components/PageLayout";

const FLOW_A = [
  "Coordinator opens AlloCare dashboard (Google Sign-In)",
  "Clicks 'Add Report' → Upload Photo",
  "Photographs paper survey or uploads existing image",
  "Cloud Vision OCR extracts text in <5 seconds",
  "Gemini analyzes text → structured urgency record",
  "Non-English? Translate API converts to English first",
  "New red/amber marker appears on the heatmap",
  "System auto-recommends top-3 matched volunteers",
  "Coordinator confirms assignment with one click",
  "'Flag incorrect score' available — human-in-the-loop always on",
];

const FLOW_B = [
  "Volunteer opens AlloCare app — sees personalized task feed",
  "Top card: 'CRITICAL — Food shortage in Dharavi · 47 families'",
  "Taps card → distance (2.3km) + required skills + impact",
  "Taps 'Accept Task' → receives Google Maps directions",
  "Arrives → taps 'Check In' (GPS-verified)",
  "Completes task → 'Mark Complete' + photo proof",
  "Animated scorecard: 'You helped 47 families today' + streak",
  "Coordinator notified · urgency score updated",
];

const FORMULAS = [
  {
    name: "Urgency Score",
    formula: "score = (severity × log(freq + 1)) ÷ max(1, days_since_first_report)",
    bands: [
      { range: "0–30", label: "LOW", color: "#0E9F6E" },
      { range: "31–60", label: "MEDIUM", color: "#E3A008" },
      { range: "61–85", label: "HIGH", color: "#F97316" },
      { range: "86–100", label: "CRITICAL", color: "#E02424" },
    ],
  },
  {
    name: "Match Score",
    formula: "match = skill_overlap × proximity × availability",
    bands: [
      { range: "skill_overlap", label: "matched_skills ÷ required_skills", color: "#1A56DB" },
      { range: "proximity", label: "1 ÷ (1 + distance_km)", color: "#1A56DB" },
      { range: "availability", label: "1 if available else 0.3", color: "#1A56DB" },
    ],
  },
];

export default function HowItWorksPage() {
  return (
    <PageLayout>
      <PageHeader
        eyebrow="How It Works"
        title="Two flows. One closed loop."
        intro="The coordinator ingests reports and the system scores them. Volunteers accept and complete the highest-impact tasks. Both ends share the same real-time data."
      />

      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-8 lg:grid-cols-2">
          <FlowCard title="Flow A · NGO Coordinator" subtitle="Ingesting a paper survey" steps={FLOW_A} accent="#1A56DB" />
          <FlowCard title="Flow B · Volunteer" subtitle="Finding and completing a task" steps={FLOW_B} accent="#0E9F6E" />
        </div>

        <h2 className="mt-20 text-2xl font-bold text-slate-900">Transparent formulas</h2>
        <p className="mt-2 text-slate-600">No black box. Both scoring formulas are visible to coordinators and judges.</p>
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          {FORMULAS.map((f) => (
            <div key={f.name} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-[#1A56DB]">{f.name}</div>
              <div className="mt-3 rounded-lg bg-slate-900 px-4 py-3 font-mono text-sm text-emerald-300">{f.formula}</div>
              <div className="mt-4 space-y-2">
                {f.bands.map((b) => (
                  <div key={b.range} className="flex items-center gap-3 rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: b.color }} />
                    <span className="font-semibold text-slate-900">{b.range}</span>
                    <span className="ml-auto text-slate-600">{b.label}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </PageLayout>
  );
}

function FlowCard({ title, subtitle, steps, accent }: { title: string; subtitle: string; steps: string[]; accent: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl text-white shadow" style={{ background: accent }}>
          ▶
        </span>
        <div>
          <div className="text-base font-bold text-slate-900">{title}</div>
          <div className="text-xs text-slate-500">{subtitle}</div>
        </div>
      </div>
      <ol className="mt-6 space-y-3">
        {steps.map((s, i) => (
          <li key={i} className="flex gap-3">
            <span className="mt-0.5 grid h-6 w-6 flex-none place-items-center rounded-full text-[11px] font-bold text-white" style={{ background: accent }}>
              {i + 1}
            </span>
            <span className="text-sm leading-relaxed text-slate-700">{s}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
