"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchRecentReports } from "@/lib/api";
import { scoreTone } from "@/lib/format";
import type { ReportSummary } from "@/lib/types";

export function RecentRuns() {
  const [reports, setReports] = useState<ReportSummary[]>([]);

  useEffect(() => {
    fetchRecentReports(6)
      .then(setReports)
      .catch(() => setReports([]));
  }, []);

  if (reports.length === 0) return null;

  return (
    <section className="no-print">
      <p className="label mb-3">Recent public reports</p>
      <ul className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {reports.map((report) => {
          const tone = scoreTone(report.overall_score ?? 0);
          return (
            <li key={report.public_id}>
              <Link
                href={`/r/${report.public_id}`}
                className="panel-tight group flex items-center justify-between gap-3 px-4 py-3 transition hover:border-white/20"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm text-slate-200">
                    {report.role_title ?? "Untitled role"}
                  </span>
                  <span className="block truncate text-xs text-slate-600">
                    {report.company ?? report.verdict ?? ""}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className={`font-mono text-sm ${tone.text}`}>
                    {report.overall_score?.toFixed(0) ?? "-"}
                  </span>
                  <ArrowUpRight className="h-3.5 w-3.5 text-slate-600 transition group-hover:text-accent" />
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
