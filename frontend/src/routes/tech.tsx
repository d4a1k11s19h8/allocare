import { PageLayout, PageHeader } from "@/components/PageLayout";

const STACK = [
  { name: "Gemini 1.5 Pro", use: "Urgency extraction + plain-English explanations + impact framing + chat Q&A", critical: "Core AI brain — every record passes through Gemini." },
  { name: "Cloud Vision API", use: "OCR on paper survey photographs — printed and handwritten field forms", critical: "Enables paper-to-digital — the #1 differentiator." },
  { name: "Google Maps Platform", use: "Heatmap layer, Distance Matrix, Geocoding, Directions for navigation", critical: "Powers all geographic intelligence." },
  { name: "Google Translate API", use: "Auto-translate Hindi, Marathi, Tamil, Bengali, Telugu reports to English", critical: "India-specific differentiator." },
  { name: "Firebase Auth", use: "Google Sign-In for NGO coordinators", critical: "Zero-friction auth — judges log in instantly." },
  { name: "Firestore", use: "Real-time NoSQL for need_reports, volunteers, assignments, organizations", critical: "Real-time sync makes the heatmap live." },
  { name: "Cloud Functions", use: "Triggered by Firestore writes (scoring), Storage uploads (OCR), HTTP (CSV import)", critical: "Serverless — no backend to manage." },
  { name: "Firebase Storage", use: "Survey photos, completion proof photos, CSV files", critical: "Required for upload flows." },
  { name: "Firebase Hosting", use: "Flutter Web build deployed for live demo URL", critical: "Free, instant deploy for judges." },
  { name: "FCM", use: "Push notifications for critical needs near volunteer", critical: "Real-time alerting." },
  { name: "Document AI", use: "Phase 2 — structured extraction from NGO form templates", critical: "Upgrade from Vision OCR." },
  { name: "Vertex AI AutoML", use: "Phase 2 — predict next-week high-urgency zones", critical: "Pre-positioning narrative." },
  { name: "BigQuery", use: "Phase 2 — cross-NGO district-level trend analytics", critical: "Shows enterprise scale planning." },
  { name: "Flutter (Google SDK)", use: "Single codebase for NGO web dashboard + volunteer mobile", critical: "Google judges reward Flutter usage." },
];

const SDGS = [
  { n: 1, title: "No Poverty", body: "Direct routing of food, water, and housing aid to families in extreme need." },
  { n: 10, title: "Reduced Inequalities", body: "Multilingual ingestion ensures non-English-speaking communities are heard." },
  { n: 17, title: "Partnerships for the Goals", body: "Multi-NGO network reduces duplicated effort across partner organizations." },
];

export default function TechPage() {
  return (
    <PageLayout>
      <PageHeader
        eyebrow="Tech Stack"
        title="All Google. End to end."
        intro="Fourteen Google services across AI, geo, data, and hosting. Built to maximize the Google Solution Challenge brief."
      />

      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-600">
              <tr>
                <th className="px-5 py-3">Google Service</th>
                <th className="px-5 py-3">Use in AlloCare</th>
                <th className="px-5 py-3">Why critical</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {STACK.map((s) => (
                <tr key={s.name} className="hover:bg-slate-50/60">
                  <td className="whitespace-nowrap px-5 py-3 font-semibold text-slate-900">{s.name}</td>
                  <td className="px-5 py-3 text-slate-700">{s.use}</td>
                  <td className="px-5 py-3 text-slate-600">{s.critical}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 className="mt-20 text-2xl font-bold text-slate-900">SDG Alignment</h2>
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          {SDGS.map((s) => (
            <div key={s.n} className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-6 shadow-sm">
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-[#1A56DB] to-[#0E9F6E] text-base font-extrabold text-white shadow">
                {s.n}
              </div>
              <h3 className="mt-4 text-lg font-semibold text-slate-900">SDG {s.n}: {s.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{s.body}</p>
            </div>
          ))}
        </div>
      </section>
    </PageLayout>
  );
}
