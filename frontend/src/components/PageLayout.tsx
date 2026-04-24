import { ReactNode } from "react";
import { SiteNav } from "./SiteNav";
import { SiteFooter } from "./SiteFooter";

export function PageLayout({ children, hero = false }: { children: ReactNode; hero?: boolean }) {
  return (
    <div className="min-h-screen bg-white">
      <SiteNav />
      <main className={hero ? "" : "pt-24"}>{children}</main>
      <SiteFooter />
    </div>
  );
}

export function PageHeader({ eyebrow, title, intro }: { eyebrow: string; title: string; intro: string }) {
  return (
    <section className="border-b border-slate-100 bg-gradient-to-b from-[#EEF4FF] to-white">
      <div className="mx-auto max-w-5xl px-6 py-16 text-center md:py-20">
        <span className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white px-3 py-1 text-xs font-semibold text-[#1A56DB] shadow-sm">
          {eyebrow}
        </span>
        <h1 className="mt-5 text-4xl font-bold tracking-tight text-slate-900 md:text-5xl" style={{ letterSpacing: "-0.02em" }}>
          {title}
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed text-slate-600">{intro}</p>
      </div>
    </section>
  );
}
