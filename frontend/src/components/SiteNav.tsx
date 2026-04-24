import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { ALLOCARE_DASHBOARD_URL } from "@/lib/allocare-config";

const NAV = [
  { to: "/problem", label: "Problem" },
  { to: "/features", label: "Features" },
  { to: "/how-it-works", label: "How It Works" },
  { to: "/research", label: "Research" },
  { to: "/tech", label: "Tech Stack" },
] as const;

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all ${
        scrolled ? "border-b border-slate-200/80 bg-white/85 backdrop-blur-md shadow-sm" : "bg-transparent"
      }`}
    >
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2 font-bold tracking-tight text-slate-900">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-[#1A56DB] to-[#0E9F6E] text-white text-sm shadow">A</span>
          AlloCare
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {NAV.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              className={`rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-100 hover:text-slate-900 ${
                location.pathname === n.to
                  ? "font-semibold text-[#1A56DB] bg-blue-50"
                  : "text-slate-600"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <a
            href={ALLOCARE_DASHBOARD_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden rounded-lg bg-gradient-to-r from-[#1A56DB] to-[#1E3A8A] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md sm:inline-flex"
          >
            Open Dashboard
          </a>
          <button
            onClick={() => setOpen((v) => !v)}
            className="rounded-md p-2 text-slate-700 md:hidden"
            aria-label="Toggle menu"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {open ? <path d="M6 6l12 12M18 6l-12 12" /> : <path d="M3 6h18M3 12h18M3 18h18" />}
            </svg>
          </button>
        </div>
      </nav>

      {open && (
        <div className="border-t border-slate-200 bg-white md:hidden">
          <div className="space-y-1 px-4 py-3">
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                onClick={() => setOpen(false)}
                className="block rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                {n.label}
              </Link>
            ))}
            <a
              href={ALLOCARE_DASHBOARD_URL}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="mt-2 block rounded-md bg-gradient-to-r from-[#1A56DB] to-[#1E3A8A] px-3 py-2 text-center text-sm font-semibold text-white"
            >
              Open Dashboard
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
