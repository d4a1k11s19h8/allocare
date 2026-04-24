// Ingest a manual text report: insert + score in one call.
// Input: { rawText, zone, lat, lng, locationText? }
// Output: { need: {...} }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const LOVABLE_API = "https://ai.gateway.lovable.dev/v1/chat/completions";

async function geminiExtract(rawText: string) {
  const apiKey = Deno.env.get("LOVABLE_API_KEY");
  if (!apiKey) throw new Error("LOVABLE_API_KEY missing");
  const tool = {
    type: "function",
    function: {
      name: "extract_need",
      description: "Extract structured humanitarian need data.",
      parameters: {
        type: "object",
        properties: {
          issue_type: { type: "string", enum: ["food", "water", "health", "housing", "education", "safety", "other"] },
          location_text: { type: "string" },
          severity_score: { type: "integer", minimum: 1, maximum: 10 },
          affected_count: { type: "integer" },
          summary: { type: "string" },
          required_skills: { type: "array", items: { type: "string" } },
          recommended_volunteer_count: { type: "integer", minimum: 1, maximum: 20 },
          language_detected: { type: "string" },
        },
        required: ["issue_type", "severity_score", "summary", "required_skills", "recommended_volunteer_count", "language_detected"],
        additionalProperties: false,
      },
    },
  };
  const resp = await fetch(LOVABLE_API, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "google/gemini-2.5-flash",
      messages: [
        { role: "system", content: "You are a humanitarian field analyst. Extract structured data from NGO field reports. Always call the extract_need tool." },
        { role: "user", content: `Extract urgency data from this field report:\n\n"${rawText}"` },
      ],
      tools: [tool],
      tool_choice: { type: "function", function: { name: "extract_need" } },
    }),
  });
  if (!resp.ok) throw new Error(`Gemini ${resp.status}: ${await resp.text()}`);
  const data = await resp.json();
  const call = data.choices?.[0]?.message?.tool_calls?.[0];
  if (!call) throw new Error("No tool call");
  return JSON.parse(call.function.arguments);
}

function computeUrgency(severity: number, freq: number, days: number) {
  const raw = (severity * Math.log(freq + 1)) / Math.max(1, days);
  const normalized = Math.min(100, Math.round(raw * 10));
  let label: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" = "LOW";
  if (normalized >= 86) label = "CRITICAL";
  else if (normalized >= 61) label = "HIGH";
  else if (normalized >= 31) label = "MEDIUM";
  return { score: normalized, label };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  try {
    const { rawText, zone, lat, lng, locationText, reporterId, orgId } = await req.json();
    if (!rawText || !zone || lat == null || lng == null) {
      return new Response(JSON.stringify({ error: "rawText, zone, lat, lng required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    const admin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const extracted = await geminiExtract(rawText);

    const since = new Date(Date.now() - 30 * 86400_000).toISOString();
    const { count: freq } = await admin
      .from("need_reports")
      .select("*", { count: "exact", head: true })
      .eq("zone", zone)
      .eq("issue_type", extracted.issue_type)
      .gte("created_at", since);

    const { score, label } = computeUrgency(extracted.severity_score, (freq ?? 0) + 1, 1);

    const { data: inserted, error } = await admin
      .from("need_reports")
      .insert({
        source: "manual",
        raw_text: rawText,
        zone,
        location_text: locationText ?? extracted.location_text ?? zone,
        lat, lng,
        issue_type: extracted.issue_type,
        severity_score: extracted.severity_score,
        affected_count: extracted.affected_count,
        summary: extracted.summary,
        required_skills: extracted.required_skills,
        recommended_volunteer_count: extracted.recommended_volunteer_count,
        language_detected: extracted.language_detected,
        urgency_score: score,
        urgency_label: label,
        reporter_id: reporterId ?? null,
        org_id: orgId ?? null,
      })
      .select()
      .single();
    if (error) throw error;

    return new Response(JSON.stringify({ need: inserted }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("ingest-need error:", e);
    const msg = e instanceof Error ? e.message : "Unknown";
    const status = msg.includes("429") ? 429 : msg.includes("402") ? 402 : 500;
    return new Response(JSON.stringify({ error: msg }), {
      status, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
