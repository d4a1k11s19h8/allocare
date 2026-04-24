// Stylized Mumbai heatmap built on a labeled SVG canvas.
// Plots need_reports by lat/lng using a simple Mumbai bounding box projection.

import { useMemo } from "react";
import { motion } from "framer-motion";

export type HeatNeed = {
  id: string;
  zone: string;
  lat: number;
  lng: number;
  urgency_score: number;
  urgency_label: string;
  issue_type: string;
  affected_count: number | null;
  summary: string | null;
};

// Mumbai bbox roughly: lat 18.89–19.27, lng 72.77–72.99
const BBOX = { latMin: 18.89, latMax: 19.27, lngMin: 72.77, lngMax: 72.99 };
const W = 600;
const H = 480;

function project(lat: number, lng: number) {
  const x = ((lng - BBOX.lngMin) / (BBOX.lngMax - BBOX.lngMin)) * W;
  const y = H - ((lat - BBOX.latMin) / (BBOX.latMax - BBOX.latMin)) * H;
  return { x, y };
}

function colorFor(label: string) {
  switch (label) {
    case "CRITICAL": return "#E02424";
    case "HIGH": return "#F97316";
    case "MEDIUM": return "#E3A008";
    default: return "#0E9F6E";
  }
}

const NEIGHBORHOODS = [
  { name: "Andheri", lat: 19.119, lng: 72.846 },
  { name: "Bandra", lat: 19.060, lng: 72.836 },
  { name: "Dharavi", lat: 19.041, lng: 72.852 },
  { name: "Kurla", lat: 19.071, lng: 72.879 },
  { name: "Govandi", lat: 19.057, lng: 72.924 },
  { name: "Worli", lat: 19.014, lng: 72.813 },
  { name: "Chembur", lat: 19.062, lng: 72.896 },
  { name: "Malad", lat: 19.186, lng: 72.836 },
  { name: "Powai", lat: 19.117, lng: 72.906 },
];

export function MumbaiHeatmap({ needs, onSelect, selectedId }: {
  needs: HeatNeed[];
  onSelect?: (n: HeatNeed) => void;
  selectedId?: string | null;
}) {
  const labels = useMemo(() => NEIGHBORHOODS.map((n) => ({ ...n, ...project(n.lat, n.lng) })), []);
  const points = useMemo(() => needs.map((n) => ({ ...n, ...project(n.lat, n.lng) })), [needs]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-slate-200 bg-[#EEF2F7]">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" className="h-full w-full">
        <defs>
          {points.map((p) => (
            <radialGradient key={`g-${p.id}`} id={`g-${p.id}`}>
              <stop offset="0%" stopColor={colorFor(p.urgency_label)} stopOpacity="0.9" />
              <stop offset="55%" stopColor={colorFor(p.urgency_label)} stopOpacity="0.35" />
              <stop offset="100%" stopColor={colorFor(p.urgency_label)} stopOpacity="0" />
            </radialGradient>
          ))}
        </defs>

        {/* Land mass */}
        <path
          d="M 30 80 Q 100 30 200 50 Q 320 25 420 70 Q 540 60 580 130 L 570 410 Q 480 460 380 430 Q 260 460 160 430 Q 60 440 30 380 Z"
          fill="#F8FAFC"
          stroke="#CBD5E1"
          strokeWidth="1.5"
        />

        {/* Major roads (decorative) */}
        {[100, 180, 260, 340, 420].map((y) => (
          <path key={y} d={`M 30 ${y} Q 300 ${y + 10} 580 ${y - 5}`} stroke="#E2E8F0" strokeWidth="1.5" fill="none" strokeDasharray="3 4" />
        ))}
        {[120, 240, 360, 480].map((x) => (
          <path key={x} d={`M ${x} 60 Q ${x + 10} 230 ${x - 5} 440`} stroke="#E2E8F0" strokeWidth="1.5" fill="none" strokeDasharray="3 4" />
        ))}

        {/* Need points */}
        {points.map((p) => {
          const radius = 18 + (p.urgency_score / 100) * 30;
          const isSel = selectedId === p.id;
          return (
            <g key={p.id} onClick={() => onSelect?.(p)} style={{ cursor: onSelect ? "pointer" : "default" }}>
              <motion.circle
                cx={p.x}
                cy={p.y}
                r={radius}
                fill={`url(#g-${p.id})`}
                animate={p.urgency_label === "CRITICAL" || p.urgency_label === "HIGH"
                  ? { opacity: [0.5, 0.9, 0.5], scale: [0.95, 1.1, 0.95] }
                  : { opacity: 0.7 }}
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
                style={{ transformOrigin: `${p.x}px ${p.y}px` }}
              />
              <circle cx={p.x} cy={p.y} r={isSel ? 7 : 5} fill={colorFor(p.urgency_label)} stroke="white" strokeWidth={isSel ? 3 : 2} />
            </g>
          );
        })}

        {/* Neighborhood labels */}
        {labels.map((l) => (
          <text key={l.name} x={l.x + 8} y={l.y - 8} fontSize="10" fontWeight="600" fill="#475569" pointerEvents="none">
            {l.name}
          </text>
        ))}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-white/90 px-3 py-2 text-[11px] backdrop-blur">
        {[["CRITICAL", "#E02424"], ["HIGH", "#F97316"], ["MEDIUM", "#E3A008"], ["LOW", "#0E9F6E"]].map(([l, c]) => (
          <span key={l} className="inline-flex items-center gap-1.5 font-medium text-slate-700">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />
            {l}
          </span>
        ))}
      </div>
    </div>
  );
}
