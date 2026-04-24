import { useEffect } from "react";
import { ALLOCARE_DASHBOARD_URL } from "@/lib/allocare-config";

export default function DashboardRedirect() {
  useEffect(() => {
    window.location.href = ALLOCARE_DASHBOARD_URL;
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-[#EEF4FF] to-white px-4">
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[#1A56DB] to-[#0E9F6E] text-2xl text-white shadow-lg">
          A
        </div>
        <h1 className="text-xl font-bold text-slate-900">Opening AlloCare Dashboard...</h1>
        <p className="mt-2 text-sm text-slate-500">
          If you are not redirected,{" "}
          <a href={ALLOCARE_DASHBOARD_URL} className="text-[#1A56DB] underline">
            click here
          </a>
          .
        </p>
      </div>
    </div>
  );
}
