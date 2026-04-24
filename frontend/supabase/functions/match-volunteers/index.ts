// Volunteer matching: computes top-3 matches for a need.
// match_score = skill_overlap × proximity × availability
// Input: { needId }
// Output: { matches: [{ volunteer_id, full_name, score, distance_km, explanation }] }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number) {
  const R = 6371;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { needId, persist = false } = await req.json();
    const admin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const { data: need, error: needErr } = await admin.from("need_reports").select("*").eq("id", needId).single();
    if (needErr || !need) throw new Error("Need not found");

    // Volunteers = profiles where user_roles has 'volunteer' (or any auth user with home_lat set)
    const { data: volunteers, error: vErr } = await admin
      .from("profiles")
      .select("id, full_name, skills, home_lat, home_lng, max_distance_km, available")
      .not("home_lat", "is", null)
      .not("home_lng", "is", null);
    if (vErr) throw vErr;

    const required: string[] = need.required_skills ?? [];
    const candidates = (volunteers ?? [])
      .map((v) => {
        const skills: string[] = v.skills ?? [];
        const overlap = required.length === 0
          ? 0.5
          : skills.filter((s) => required.some((r) => r.toLowerCase().includes(s.toLowerCase()) || s.toLowerCase().includes(r.toLowerCase()))).length / required.length;
        const dist = haversineKm(v.home_lat!, v.home_lng!, need.lat, need.lng);
        if (dist > (v.max_distance_km ?? 10)) return null;
        const proximity = 1 / (1 + dist);
        const avail = v.available ? 1 : 0.3;
        const score = overlap * proximity * avail;
        const matched = skills.filter((s) => required.some((r) => r.toLowerCase().includes(s.toLowerCase()) || s.toLowerCase().includes(r.toLowerCase())));
        const explanation = `Matched: ${matched.length > 0 ? matched.join(", ") + " ✓ · " : ""}${dist.toFixed(1)}km away ✓${v.available ? " · Available now ✓" : ""}`;
        return { volunteer_id: v.id, full_name: v.full_name, score, distance_km: dist, explanation };
      })
      .filter(Boolean)
      .sort((a, b) => b!.score - a!.score)
      .slice(0, 3) as Array<{ volunteer_id: string; full_name: string; score: number; distance_km: number; explanation: string }>;

    if (persist && candidates.length > 0) {
      const rows = candidates.map((c) => ({
        need_id: needId,
        volunteer_id: c.volunteer_id,
        match_score: c.score,
        distance_km: c.distance_km,
        explanation: c.explanation,
        status: "suggested" as const,
      }));
      await admin.from("assignments").upsert(rows, { onConflict: "need_id,volunteer_id" });
    }

    return new Response(JSON.stringify({ matches: candidates }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("match-volunteers error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
