// Gemini-powered urgency scoring for a single need report.
// Input: { needId: string } OR { rawText, zone, lat, lng } for ad-hoc preview
// Output: scored fields written to need_reports if needId given.

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
      description: "Extract structured humanitarian need data from a field report.",
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

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Gemini error ${resp.status}: ${text}`);
  }
  const data = await resp.json();
  const call = data.choices?.[0]?.message?.tool_calls?.[0];
  if (!call) throw new Error("No tool call in Gemini response");
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
    const body = await req.json();
    const { needId } = body;

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const admin = createClient(supabaseUrl, serviceKey);

    let need: any;
    if (needId) {
      const { data, error } = await admin.from("need_reports").select("*").eq("id", needId).single();
      if (error) throw error;
      need = data;
    } else {
      need = body;
    }

    const extracted = await geminiExtract(need.raw_text);

    // Frequency = same zone+issue in last 30 days
    const since = new Date(Date.now() - 30 * 86400_000).toISOString();
    const { count: freq } = await admin
      .from("need_reports")
      .select("*", { count: "exact", head: true })
      .eq("zone", need.zone)
      .eq("issue_type", extracted.issue_type)
      .gte("created_at", since);

    const days = Math.max(1, Math.floor((Date.now() - new Date(need.first_reported_at ?? need.created_at ?? Date.now()).getTime()) / 86400_000));
    const { score, label } = computeUrgency(extracted.severity_score, (freq ?? 0) + 1, days);

    const update = {
      issue_type: extracted.issue_type,
      severity_score: extracted.severity_score,
      affected_count: extracted.affected_count ?? null,
      summary: extracted.summary,
      required_skills: extracted.required_skills,
      recommended_volunteer_count: extracted.recommended_volunteer_count,
      language_detected: extracted.language_detected,
      location_text: extracted.location_text ?? need.location_text,
      urgency_score: score,
      urgency_label: label,
    };

    if (needId) {
      const { error: upErr } = await admin.from("need_reports").update(update).eq("id", needId);
      if (upErr) throw upErr;
    }

    return new Response(JSON.stringify({ ok: true, scored: update, frequency: freq ?? 0, days }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("score-need error:", e);
    const msg = e instanceof Error ? e.message : "Unknown error";
    const status = msg.includes("429") ? 429 : msg.includes("402") ? 402 : 500;
    return new Response(JSON.stringify({ error: msg }), {
      status,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
