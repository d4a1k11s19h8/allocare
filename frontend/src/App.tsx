import { Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";

// Eager-loaded main page
import { IndexPage } from "./routes/index";

// Lazy-loaded secondary pages
const FeaturesPage = lazy(() => import("./routes/features"));
const HowItWorksPage = lazy(() => import("./routes/how-it-works"));
const ProblemPage = lazy(() => import("./routes/problem"));
const ResearchPage = lazy(() => import("./routes/research"));
const TechPage = lazy(() => import("./routes/tech"));
const AuthRedirect = lazy(() => import("./routes/auth"));
const DashboardRedirect = lazy(() => import("./routes/dashboard"));
const VolunteerRedirect = lazy(() => import("./routes/volunteer"));

function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-[#1A56DB]" />
    </div>
  );
}

export function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/" element={<IndexPage />} />
        <Route path="/features" element={<FeaturesPage />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/problem" element={<ProblemPage />} />
        <Route path="/research" element={<ResearchPage />} />
        <Route path="/tech" element={<TechPage />} />
        <Route path="/auth" element={<AuthRedirect />} />
        <Route path="/dashboard" element={<DashboardRedirect />} />
        <Route path="/volunteer" element={<VolunteerRedirect />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}

function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-slate-900">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-slate-900">Page not found</h2>
        <p className="mt-2 text-sm text-slate-500">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md bg-gradient-to-r from-[#1A56DB] to-[#1E3A8A] px-4 py-2 text-sm font-medium text-white transition-colors hover:shadow-md"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}
