import { PageLayout, PageHeader } from "@/components/PageLayout";

const P0 = [
  { id: "F1", icon: "📥", title: "Multi-Source Data Ingestion", body: "Paper photo → Cloud Vision OCR. CSV/XLSX bulk import. Manual text entry. WhatsApp/SMS via Twilio webhook. Every channel converges into structured records.", metric: "<5s ingest · >90% English / >80% Hindi accuracy" },
  { id: "F2", icon: "🧠", title: "Gemini Urgency Scoring", body: "Firestore-triggered Cloud Function sends extracted text to Gemini. Returns issue type, severity (1–10), affected count, plain-English summary, recommended skills, and an urgency score 0–100.", metric: "Transparent formula: severity × log(freq+1) ÷ days" },
  { id: "F3", icon: "🗺️", title: "Google Maps Urgency Heatmap", body: "deck.gl HeatmapLayer over Google Maps. Green→amber→orange→red gradient. Click clusters to expand individual need cards. District choropleth view.", metric: "Real-time updates via Firestore listeners" },
  { id: "F4", icon: "🎯", title: "Smart Volunteer Matching", body: "match_score = skill_overlap × proximity × availability. Top-3 ranked matches per need with explainability: 'Medical First Aid ✓, 2.3km away ✓, Available Saturday ✓'.", metric: "Google Maps Distance Matrix for real travel times" },
  { id: "F5", icon: "📊", title: "NGO Coordinator Dashboard", body: "Left panel: urgency-ranked need feed. Center: heatmap. Right: volunteer pool. Bottom: 30-day impact analytics. One-click assignment confirmation.", metric: "Google Sign-In · Real-time sync" },
  { id: "F6", icon: "📱", title: "Volunteer Mobile Task Feed", body: "Personalized feed by match score. Each card: urgency badge, impact framing, skills, distance, time estimate. Accept → GPS check-in → completion photo.", metric: "Push notifications for critical nearby needs" },
  { id: "F7", icon: "🏅", title: "Impact Scorecard & Gamification", body: "Animated post-task scorecard: families helped, urgency rank resolved, cumulative hours, community rank, streak badges.", metric: "+40% volunteer retention (SSRN, 2025)" },
];

const P1 = [
  { id: "F8", icon: "🌐", title: "Multilingual Support", body: "Auto-detect + translate Hindi, Marathi, Tamil, Bengali, Telugu reports before NLP. India-specific differentiator." },
  { id: "F9", icon: "🔮", title: "Predictive Forecasting", body: "Vertex AI AutoML predicts where urgency will spike 7 days ahead based on historical patterns." },
  { id: "F10", icon: "🤝", title: "Multi-NGO Network", body: "Organizations share anonymized urgency data to avoid duplication. City-wide visibility layer." },
  { id: "F11", icon: "📡", title: "KoBoToolbox Integration", body: "Live API feed from KoBoToolbox submissions. No manual export required." },
  { id: "F12", icon: "📴", title: "Offline Mode", body: "Flutter app works offline with local SQLite cache. Syncs when connectivity returns. Critical for rural India." },
];

export default function FeaturesPage() {
  return (
    <PageLayout>
      <PageHeader
        eyebrow="Features"
        title="Everything needed to close the loop — from paper to deployed volunteer."
        intro="Seven P0 features ship in Phase 1. Five P1 features extend the platform for scale, multilingual coverage, and predictive ops."
      />

      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="flex items-end justify-between">
          <h2 className="text-2xl font-bold text-slate-900">Phase 1 — Core Platform</h2>
          <span className="rounded-full bg-[#0E9F6E]/10 px-3 py-1 text-xs font-semibold text-[#0E9F6E]">P0 · Must Ship</span>
        </div>
        <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {P0.map((f) => (
            <article key={f.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-center justify-between">
                <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-blue-50 to-emerald-50 text-2xl">{f.icon}</div>
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-600">{f.id}</span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.body}</p>
              <div className="mt-4 border-t border-slate-100 pt-3 text-[11px] font-medium text-[#1A56DB]">{f.metric}</div>
            </article>
          ))}
        </div>

        <div className="mt-20 flex items-end justify-between">
          <h2 className="text-2xl font-bold text-slate-900">Phase 2 — Enhancements</h2>
          <span className="rounded-full bg-[#E3A008]/10 px-3 py-1 text-xs font-semibold text-[#E3A008]">P1</span>
        </div>
        <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {P1.map((f) => (
            <article key={f.id} className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 p-6">
              <div className="flex items-center justify-between">
                <div className="text-2xl">{f.icon}</div>
                <span className="rounded-md bg-white px-2 py-0.5 text-[11px] font-bold text-slate-600">{f.id}</span>
              </div>
              <h3 className="mt-4 text-base font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.body}</p>
            </article>
          ))}
        </div>
      </section>
    </PageLayout>
  );
}
