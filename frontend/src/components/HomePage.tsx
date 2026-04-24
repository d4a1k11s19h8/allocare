import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Hero } from "./Hero";
import { ALLOCARE_DASHBOARD_URL } from "@/lib/allocare-config";

const FAILURES = [
  {
    icon: "📄",
    title: "Data is Undigitized",
    body: "Paper surveys and handwritten field reports cannot be analyzed at scale. Critical patterns — seasonal hunger spikes, recurring flood areas — stay invisible to any digital tool.",
    accent: "#E02424",
  },
  {
    icon: "🧩",
    title: "Data is Siloed",
    body: "Even when digitized, need-data lives across WhatsApp threads, individual Google Sheets, and email chains. No unified view exists to compare urgency across areas or organizations.",
    accent: "#E3A008",
  },
  {
    icon: "📞",
    title: "Matching is Manual",
    body: "Volunteer coordinators assign tasks through personal knowledge and phone calls. Slow, non-scalable, language-limited, and systematically misses the best-fit assignments.",
    accent: "#1A56DB",
  },
];

const PIPELINE = [
  {
    step: "01",
    title: "Multi-source ingestion",
    body: "Photo of paper survey, CSV/XLSX bulk import, manual entry, or WhatsApp/SMS — all roads converge into one structured stream.",
  },
  {
    step: "02",
    title: "Gemini urgency intelligence",
    body: "Every record is scored, clustered, and visualized. Transparent formula: severity × log(frequency + 1) ÷ days. No black box.",
  },
  {
    step: "03",
    title: "Smart volunteer matching",
    body: "Skill overlap × proximity × availability. The right person reaches the highest-priority task in real time.",
  },
];

const STATS = [
  { value: "60%", label: "less data-entry time", source: "arXiv:2510.15509 (2025)" },
  { value: "30%", label: "faster resource allocation", source: "arXiv:2510.15509 (2025)" },
  { value: "40%", label: "higher volunteer retention with impact framing", source: "SSRN (2025)" },
  { value: "1,000", label: "NGOs in 12-month India scale target", source: "AlloCare roadmap" },
];

export function HomePage() {
  return (
    <>
      <Hero />

      {/* Problem */}
      <section className="border-y border-slate-100 bg-slate-50/60 py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-red-100 bg-red-50 px-3 py-1 text-xs font-semibold text-[#E02424]">
              The Problem
            </span>
            <h2 className="mt-5 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl" style={{ letterSpacing: "-0.02em" }}>
              Resources aren't lacking. <span className="text-[#E02424]">Visibility is.</span>
            </h2>
            <p className="mt-4 text-lg text-slate-600">
              Local NGOs collect valuable need-data through paper, WhatsApp, and field visits. It sits siloed —
              no system aggregates urgency, no bridge routes volunteers to where they're needed most.
            </p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {FAILURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl text-xl" style={{ background: `${f.accent}14` }}>
                  {f.icon}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-slate-900">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution pipeline */}
      <section className="py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-xs font-semibold text-[#1A56DB]">
              The Solution
            </span>
            <h2 className="mt-5 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl" style={{ letterSpacing: "-0.02em" }}>
              A three-layer intelligent pipeline
            </h2>
            <p className="mt-4 text-lg text-slate-600">
              AlloCare = Allocation + Care. From scattered field signals to deployed humans, in one continuous flow.
            </p>
          </div>
          <div className="relative mt-14 grid gap-8 md:grid-cols-3">
            <div aria-hidden className="absolute left-12 right-12 top-12 hidden h-px bg-gradient-to-r from-[#1A56DB] via-[#0E9F6E] to-[#E3A008] md:block" />
            {PIPELINE.map((p, i) => (
              <motion.div
                key={p.step}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="relative rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-[#1A56DB] to-[#1E3A8A] text-sm font-bold text-white shadow-md">
                  {p.step}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-slate-900">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{p.body}</p>
              </motion.div>
            ))}
          </div>
          <div className="mt-12 flex justify-center">
            <Link
              to="/how-it-works"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 shadow-sm hover:border-[#1A56DB] hover:text-[#1A56DB]"
            >
              See the full flow →
            </Link>
          </div>
        </div>
      </section>

      {/* Impact stats */}
      <section className="border-y border-slate-100 bg-gradient-to-br from-[#0F172A] to-[#1E3A8A] py-20 text-white">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider">
              Research-Backed Impact
            </span>
            <h2 className="mt-5 text-3xl font-bold tracking-tight md:text-4xl" style={{ letterSpacing: "-0.02em" }}>
              Numbers that justify AI-first humanitarian tooling
            </h2>
          </div>
          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {STATS.map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.5, delay: i * 0.06 }}
                className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur"
              >
                <div className="bg-gradient-to-br from-white via-white to-blue-200 bg-clip-text text-4xl font-extrabold text-transparent">
                  {s.value}
                </div>
                <div className="mt-2 text-sm font-medium text-white/90">{s.label}</div>
                <div className="mt-3 text-[11px] uppercase tracking-wider text-white/50">{s.source}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-900 md:text-4xl" style={{ letterSpacing: "-0.02em" }}>
            Ready to deploy the right person, faster?
          </h2>
          <p className="mt-4 text-lg text-slate-600">
            Sign in as a coordinator to ingest reports and match volunteers — or join as a volunteer to see needs near you.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <a
              href={ALLOCARE_DASHBOARD_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#1A56DB] to-[#1E3A8A] px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 hover:shadow-xl"
            >
              Get Early Access
            </a>
            <a
              href={ALLOCARE_DASHBOARD_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-800 hover:border-[#1A56DB] hover:text-[#1A56DB]"
            >
              View Live Dashboard
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
