import { API_BASE } from "@/lib/api";

export function Footer() {
  return (
    <footer className="no-print mt-20 border-t border-white/[0.06]">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-5 py-8 text-xs text-slate-600 sm:flex-row sm:items-center sm:justify-between">
        <p>
          FitScope — built by{" "}
          <a
            href="https://github.com/shahriar-ahmed-seam"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 transition hover:text-white"
          >
            Shahriar Ahmed Seam
          </a>
          . Resumes are parsed in memory and discarded; only the analysis is stored.
        </p>
        <div className="flex flex-wrap gap-4">
          <a
            href={`${API_BASE}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="transition hover:text-slate-300"
          >
            OpenAPI docs
          </a>
          <a
            href={`${API_BASE}/api/v1/scoring`}
            target="_blank"
            rel="noopener noreferrer"
            className="transition hover:text-slate-300"
          >
            Scoring weights
          </a>
          <a
            href="https://www.pexels.com/photo/modern-laptop-on-wooden-desk-with-code-displayed-34803994/"
            target="_blank"
            rel="noopener noreferrer"
            className="transition hover:text-slate-300"
          >
            Hero photo: Daniil Komov / Pexels
          </a>
        </div>
      </div>
    </footer>
  );
}
