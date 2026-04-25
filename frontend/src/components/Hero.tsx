import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

const COLORS = {
  blue: "#1A56DB",
  blueDeep: "#1E3A8A",
  green: "#0E9F6E",
  red: "#E02424",
  amber: "#E3A008",
  slate: "#334155",
  slateMuted: "#64748B",
};

type Need = {
  id: number;
  icon: string;
  title: string;
  meta: string;
  accent: string;
};

const NEEDS: Need[] = [
  {
    id: 1,
    icon: "🔴",
    title: "47 families affected",
    meta: "Food shortage · Dharavi",
    accent: COLORS.red,
  },
  {
    id: 2,
    icon: "🟠",
    title: "Water contamination",
    meta: "Kurla West · 12 households",
    accent: COLORS.amber,
  },
  {
    id: 3,
    icon: "✅",
    title: "Matched: Priya S.",
    meta: "En route · 2.3 km away",
    accent: COLORS.green,
  },
];

type Cluster = {
  id: string;
  cx: number;
  cy: number;
  r: number;
  color: string;
  label: string;
  delay: number;
};

const CLUSTERS: Cluster[] = [
  { id: "dharavi", cx: 180, cy: 230, r: 38, color: COLORS.red, label: "Dharavi", delay: 0 },
  { id: "kurla", cx: 280, cy: 200, r: 34, color: COLORS.red, label: "Kurla", delay: 0.6 },
  { id: "govandi", cx: 320, cy: 280, r: 30, color: COLORS.red, label: "Govandi", delay: 1.2 },
  { id: "bandra", cx: 150, cy: 160, r: 26, color: COLORS.amber, label: "Bandra E", delay: 0.3 },
];

const LOW_ZONES = [
  { cx: 90, cy: 100, r: 60 },
  { cx: 380, cy: 120, r: 55 },
  { cx: 100, cy: 320, r: 50 },
  { cx: 380, cy: 330, r: 65 },
];

const ROADS = [
  "M 0 90 Q 200 110 460 80",
  "M 0 180 Q 220 200 460 170",
  "M 0 260 Q 200 280 460 250",
  "M 0 340 Q 220 360 460 330",
  "M 90 0 Q 110 200 130 400",
  "M 230 0 Q 250 200 270 400",
  "M 360 0 Q 380 200 400 400",
];

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

export function Hero() {
  const [needIndex, setNeedIndex] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setNeedIndex((i) => (i + 1) % NEEDS.length), 3500);
    return () => clearInterval(t);
  }, []);

  const currentNeed = NEEDS[needIndex];

  return (
    <section
      className="relative min-h-screen w-full overflow-hidden"
      style={{
        background: "linear-gradient(180deg, #EEF4FF 0%, #F7FAFF 55%, #FFFFFF 100%)",
      }}
    >
      {/* Dotted grid overlay */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "radial-gradient(circle, rgba(26,86,219,0.08) 1px, transparent 1px)",
          backgroundSize: "22px 22px",
        }}
      />
      {/* Soft blue blobs */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 -right-40 h-[480px] w-[480px] rounded-full blur-3xl"
        style={{ background: "radial-gradient(circle, rgba(26,86,219,0.18), transparent 70%)" }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-40 -left-32 h-[420px] w-[420px] rounded-full blur-3xl"
        style={{ background: "radial-gradient(circle, rgba(14,159,110,0.14), transparent 70%)" }}
      />

      <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col items-center justify-center gap-10 px-6 py-20 lg:flex-row lg:gap-12 lg:py-24">
        {/* LEFT: Copy */}
        <motion.div
          initial="hidden"
          animate="visible"
          transition={{ staggerChildren: 0.12, delayChildren: 0.1 }}
          className="flex w-full flex-col lg:w-1/2"
        >
          <motion.span
            variants={fadeUp}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="inline-flex w-fit items-center gap-2 rounded-full border border-blue-100 bg-white/70 px-3.5 py-1.5 text-xs font-semibold tracking-wide text-[#1A56DB] shadow-sm backdrop-blur"
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#1A56DB] opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-[#1A56DB]" />
            </span>
            AI-Powered Volunteer Coordination
          </motion.span>

          <motion.h1
            variants={fadeUp}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="mt-6 font-bold tracking-tight text-slate-900"
            style={{
              fontSize: "clamp(2.25rem, 5.2vw, 4rem)",
              lineHeight: 1.05,
              letterSpacing: "-0.02em",
            }}
          >
            From Paper Survey to{" "}
            <span
              style={{
                background: `linear-gradient(135deg, ${COLORS.blue} 0%, ${COLORS.blueDeep} 100%)`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              Matched Volunteer
            </span>{" "}
            in 60 Seconds
          </motion.h1>

          <motion.p
            variants={fadeUp}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="mt-6 max-w-xl text-slate-600"
            style={{ fontSize: "clamp(1rem, 1.4vw, 1.25rem)", lineHeight: 1.6 }}
          >
            AlloCare transforms scattered NGO field reports into ranked urgency signals and
            instantly deploys the right volunteers: closing the loop from problem to action.
          </motion.p>

          <motion.div
            variants={fadeUp}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <motion.button
              whileHover={{ y: -2, boxShadow: "0 18px 38px -12px rgba(26,86,219,0.55)" }}
              whileTap={{ y: 0 }}
              transition={{ type: "spring", stiffness: 280, damping: 20 }}
              className="group inline-flex items-center gap-2 rounded-xl px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/25"
              style={{
                background: `linear-gradient(135deg, ${COLORS.blue} 0%, ${COLORS.blueDeep} 100%)`,
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z" />
              </svg>
              Watch Live Demo
            </motion.button>

            <motion.button
              whileHover={{ y: -2, backgroundColor: "rgba(26,86,219,0.06)" }}
              whileTap={{ y: 0 }}
              transition={{ type: "spring", stiffness: 280, damping: 20 }}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white/70 px-6 py-3.5 text-sm font-semibold text-slate-800 backdrop-blur"
            >
              View Research
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 17 17 7M7 7h10v10" />
              </svg>
            </motion.button>
          </motion.div>

          <motion.div
            variants={fadeUp}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500"
          >
            <span className="font-medium">Built for Google Solution Challenge 2026</span>
            <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline-block" />
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Aligned with</span>
              {[1, 10, 17].map((n) => (
                <span
                  key={n}
                  className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-[#1A56DB] to-[#0E9F6E] text-[10px] font-bold text-white shadow-sm"
                  title={`UN SDG ${n}`}
                >
                  {n}
                </span>
              ))}
              <span className="ml-1 font-semibold text-slate-700">UN SDGs</span>
            </div>
          </motion.div>
        </motion.div>

        {/* RIGHT: Mockup */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
          className="relative w-full lg:w-1/2"
        >
          <div className="relative mx-auto w-full max-w-[560px]">
            {/* Floating badges */}
            <FloatingBadge
              className="absolute -left-2 -top-4 z-30 sm:-left-6"
              delay={0}
              icon="✨"
              text="Gemini AI Powered"
            />
            <FloatingBadge
              className="absolute -right-2 top-16 z-30 sm:-right-6"
              delay={1}
              icon="🗺"
              text="Google Maps Platform"
            />
            <FloatingBadge
              className="absolute -bottom-4 left-6 z-30 sm:-bottom-6"
              delay={2}
              icon="🎯"
              text="SDG 17 Aligned"
            />

            {/* Browser frame */}
            <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_30px_80px_-20px_rgba(15,23,42,0.25)]">
              {/* Chrome */}
              <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50/80 px-4 py-3">
                <div className="flex gap-1.5">
                  <span className="h-3 w-3 rounded-full bg-[#FF5F57]" />
                  <span className="h-3 w-3 rounded-full bg-[#FEBC2E]" />
                  <span className="h-3 w-3 rounded-full bg-[#28C840]" />
                </div>
                <div className="ml-3 flex flex-1 items-center gap-2 rounded-md bg-white px-3 py-1.5 text-[11px] text-slate-500 shadow-inner">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  allocare.app/dashboard
                </div>
              </div>

              {/* Map area */}
              <div className="relative aspect-[4/3.2] w-full overflow-hidden bg-[#F1F5F9]">
                <svg
                  viewBox="0 0 460 400"
                  preserveAspectRatio="xMidYMid slice"
                  className="absolute inset-0 h-full w-full"
                >
                  <defs>
                    {CLUSTERS.map((c) => (
                      <radialGradient key={`g-${c.id}`} id={`g-${c.id}`}>
                        <stop offset="0%" stopColor={c.color} stopOpacity="0.85" />
                        <stop offset="60%" stopColor={c.color} stopOpacity="0.35" />
                        <stop offset="100%" stopColor={c.color} stopOpacity="0" />
                      </radialGradient>
                    ))}
                    <radialGradient id="g-low">
                      <stop offset="0%" stopColor={COLORS.green} stopOpacity="0.35" />
                      <stop offset="100%" stopColor={COLORS.green} stopOpacity="0" />
                    </radialGradient>
                  </defs>

                  {/* Base map fill */}
                  <rect width="460" height="400" fill="#EEF2F7" />

                  {/* Land mass shape */}
                  <path
                    d="M 30 60 Q 80 30 160 50 Q 240 30 320 60 Q 400 50 440 100 L 430 340 Q 380 380 300 360 Q 220 380 140 360 Q 60 370 25 320 Z"
                    fill="#F8FAFC"
                    stroke="#E2E8F0"
                    strokeWidth="1.5"
                  />

                  {/* Diffuse green low-urgency wash */}
                  {LOW_ZONES.map((z, i) => (
                    <circle key={i} cx={z.cx} cy={z.cy} r={z.r} fill="url(#g-low)" />
                  ))}

                  {/* Roads */}
                  {ROADS.map((d, i) => (
                    <path
                      key={i}
                      d={d}
                      stroke="#CBD5E1"
                      strokeWidth="1.5"
                      fill="none"
                      strokeDasharray="3 4"
                      opacity="0.7"
                    />
                  ))}

                  {/* Critical/amber clusters with pulsing glow */}
                  {CLUSTERS.map((c) => (
                    <g key={c.id}>
                      <motion.circle
                        cx={c.cx}
                        cy={c.cy}
                        r={c.r * 1.6}
                        fill={`url(#g-${c.id})`}
                        animate={{ opacity: [0.4, 0.85, 0.4], scale: [0.9, 1.15, 0.9] }}
                        transition={{
                          duration: 2,
                          repeat: Infinity,
                          ease: "easeInOut",
                          delay: c.delay,
                        }}
                        style={{ transformOrigin: `${c.cx}px ${c.cy}px` }}
                      />
                      <circle cx={c.cx} cy={c.cy} r={6} fill={c.color} />
                      <circle cx={c.cx} cy={c.cy} r={3} fill="white" />
                      <text
                        x={c.cx + 10}
                        y={c.cy - 8}
                        fontSize="10"
                        fontWeight="600"
                        fill="#1E293B"
                      >
                        {c.label}
                      </text>
                    </g>
                  ))}

                  {/* Other neighborhood labels */}
                  <text x="60" y="80" fontSize="9" fill="#94A3B8" fontWeight="500">Andheri</text>
                  <text x="380" y="80" fontSize="9" fill="#94A3B8" fontWeight="500">Powai</text>
                  <text x="80" y="350" fontSize="9" fill="#94A3B8" fontWeight="500">Worli</text>
                </svg>

                {/* Floating need card */}
                <div className="absolute left-4 top-4 right-4 sm:left-auto sm:right-4 sm:max-w-[260px]">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={currentNeed.id}
                      initial={{ opacity: 0, y: -8, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -8, scale: 0.96 }}
                      transition={{ duration: 0.45, ease: "easeOut" }}
                      className="rounded-xl border border-slate-200 bg-white/95 p-3 shadow-lg backdrop-blur"
                    >
                      <div className="flex items-start gap-2.5">
                        <span
                          className="mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-lg text-sm"
                          style={{ background: `${currentNeed.accent}1A` }}
                        >
                          {currentNeed.icon}
                        </span>
                        <div className="min-w-0">
                          <div className="text-[13px] font-semibold text-slate-900">
                            {currentNeed.title}
                          </div>
                          <div className="text-[11px] text-slate-500">{currentNeed.meta}</div>
                        </div>
                      </div>
                    </motion.div>
                  </AnimatePresence>
                </div>
              </div>

              {/* Live ticker */}
              <div className="flex items-center justify-between gap-3 border-t border-slate-100 bg-gradient-to-r from-[#1A56DB] to-[#1E3A8A] px-4 py-2.5 text-[11px] font-medium text-white">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-white" />
                  </span>
                  <span>Urgency score: 92/100</span>
                </div>
                <span className="opacity-90">Top match found in 8s</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function FloatingBadge({
  className,
  delay,
  icon,
  text,
}: {
  className?: string;
  delay: number;
  icon: string;
  text: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: [0, -6, 0] }}
      transition={{
        opacity: { duration: 0.6, delay: 0.6 + delay * 0.15 },
        y: { duration: 3.5 + delay * 0.4, repeat: Infinity, ease: "easeInOut", delay: delay * 0.3 },
      }}
      className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/95 px-3 py-1.5 text-[11px] font-semibold text-slate-700 shadow-md backdrop-blur ${className ?? ""}`}
    >
      <span>{icon}</span>
      {text}
    </motion.div>
  );
}
