import Link from "next/link";
import { Github, Target } from "lucide-react";

import { API_BASE } from "@/lib/api";

export function Nav() {
  return (
    <header className="no-print sticky top-0 z-40 border-b border-white/[0.06] bg-ink-950/80 backdrop-blur-md">
      <nav className="mx-auto flex h-14 w-full max-w-6xl items-center gap-6 px-5">
        <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-white">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15 text-accent">
            <Target className="h-4 w-4" />
          </span>
          FitScope
        </Link>

        <div className="ml-auto flex items-center gap-5 text-sm">
          <Link href="/how-it-works" className="text-slate-400 transition hover:text-white">
            How it works
          </Link>
          <a
            href={`${API_BASE}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden text-slate-400 transition hover:text-white sm:inline"
          >
            API
          </a>
          <a
            href="https://github.com/shahriar-ahmed-seam/fitscope"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 transition hover:text-white"
            aria-label="Source on GitHub"
          >
            <Github className="h-4 w-4" />
          </a>
        </div>
      </nav>
    </header>
  );
}
