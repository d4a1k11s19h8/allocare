import { PageLayout, PageHeader } from "@/components/PageLayout";

const PAPERS = [
  { id: "P1", title: "AI Adoption in NGOs: Systematic Literature Review", source: "arXiv:2510.15509 (2025) · 65 NGOs", finding: "AI reduced data entry by 60% and resource allocation time by 30%.", use: "Foundational justification for building AI-first. Cited in pitch opening." },
  { id: "P2", title: "Improving Humanitarian Needs Assessments through NLP", source: "IBM/IEEE (2020)", finding: "NLP can transcribe, translate and analyze qualitative field reports at scale.", use: "Technical justification for the Gemini OCR + NLP pipeline on paper forms." },
  { id: "P3", title: "NLP for Humanitarian Action: Field Tools Survey", source: "Frontiers in Big Data (2023)", finding: "KoBoToolbox and UNICEF U-Report already work in the field: build ingestion, not collection.", use: "Shapes the 'connect to existing tools' architecture. Justifies KoBoToolbox import." },
  { id: "P4", title: "AI-Driven Digital Volunteering for NGOs", source: "ResearchGate (2025)", finding: "AI matching by urgency + skill is effective during rapid-response; gamification improves retention.", use: "Justifies matching algorithm design and impact-scorecard gamification." },
  { id: "P5", title: "Volunteer Engagement & Intrinsic Impact Framing", source: "SSRN (2025)", finding: "Intrinsic-impact framing increases volunteer retention by 40% vs. extrinsic rewards alone.", use: "Drives the impact-scorecard copy and post-task animation design." },
  { id: "P6", title: "Real-time Geographic Heatmaps for Crisis Response", source: "deck.gl + Google Maps (2025)", finding: "deck.gl HeatmapLayer is the modern replacement after native heatmap deprecation (May 2025).", use: "Architectural choice for the urgency heatmap rendering layer." },
];

export default function ResearchPage() {
  return (
    <PageLayout>
      <PageHeader
        eyebrow="Research"
        title="Evidence-grounded, not vibes-driven."
        intro="Every major design decision in AlloCare maps to a peer-reviewed finding. Judges reward solutions backed by published evidence."
      />
      <section className="mx-auto max-w-5xl px-6 py-16">
        <div className="space-y-4">
          {PAPERS.map((p) => (
            <article key={p.id} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-[80px_1fr]">
              <div>
                <div className="grid h-14 w-14 place-items-center rounded-xl bg-gradient-to-br from-[#1A56DB] to-[#1E3A8A] text-sm font-bold text-white shadow">
                  {p.id}
                </div>
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-900">{p.title}</h3>
                <div className="mt-1 text-xs font-medium text-slate-500">{p.source}</div>
                <div className="mt-3 rounded-lg border-l-2 border-[#0E9F6E] bg-emerald-50/50 px-3 py-2 text-sm italic text-slate-800">
                  "{p.finding}"
                </div>
                <div className="mt-3 text-sm text-slate-700">
                  <span className="font-semibold text-[#1A56DB]">Used in AlloCare: </span>{p.use}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </PageLayout>
  );
}
