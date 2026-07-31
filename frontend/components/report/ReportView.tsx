"use client";

import { motion } from "framer-motion";
import { Download, Link2, Printer, RotateCcw } from "lucide-react";

import { markdownUrl } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { AnalysisReport } from "@/lib/types";
import { CopyButton, Stat } from "@/components/ui/Primitives";

import { AtsPanel } from "./AtsPanel";
import { EvidenceList } from "./EvidenceList";
import { ScoreSummary } from "./ScoreSummary";
import { SuggestionsPanel } from "./SuggestionsPanel";

function PipelineFooter({ report }: { report: AnalysisReport }) {
  const { pipeline, resume_stats: stats } = report;
  const rows: [string, string][] = [
    ["JD extraction", String(pipeline.jd_extraction ?? "-")],
    ["Retrieval", String(pipeline.retrieval ?? "-")],
    ["Coverage decision", String(pipeline.decider ?? "-")],
    ["Rewrites", String(pipeline.suggestions ?? "-")],
    ["Requirements", String(pipeline.requirement_count ?? report.evidence.length)],
    ["Resume lines indexed", String(pipeline.candidate_lines ?? stats.bullet_count ?? "-")],
  ];

  return (
    <section className="panel p-5">
      <p className="label mb-3">How this report was produced</p>
      <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map(([key, value]) => (
          <div key={key} className="flex items-baseline justify-between gap-3 border-b border-white/[0.04] pb-1.5">
            <dt className="text-xs text-slate-500">{key}</dt>
            <dd className="font-mono text-xs text-slate-300 print-text">{value}</dd>
          </div>
        ))}
      </dl>
      {stats.parse_warnings && stats.parse_warnings.length > 0 ? (
        <ul className="mt-4 space-y-1.5">
          {stats.parse_warnings.map((warning) => (
            <li key={warning} className="text-xs text-amber-300/80">
              Parser note: {warning}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function ReportView({
  report,
  onReset,
  shared = false,
}: {
  report: AnalysisReport;
  onReset?: () => void;
  shared?: boolean;
}) {
  const stats = report.resume_stats;
  const shareUrl =
    report.share_url ??
    (report.public_id && typeof window !== "undefined"
      ? `${window.location.origin}/r/${report.public_id}`
      : null);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-500">
          {report.created_at ? `Generated ${formatDate(report.created_at)}` : "Fresh analysis"}
          {report.public_id ? ` · id ${report.public_id}` : ""}
        </p>
        <div className="flex flex-wrap gap-2">
          {onReset ? (
            <button type="button" onClick={onReset} className="btn-ghost">
              <RotateCcw className="h-4 w-4" />
              New analysis
            </button>
          ) : null}
          {shareUrl ? (
            <CopyButton text={shareUrl} label="Copy share link" className="px-3 py-2.5" />
          ) : null}
          {report.public_id ? (
            <a
              className="btn-ghost"
              href={markdownUrl(report.public_id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Download className="h-4 w-4" />
              Markdown
            </a>
          ) : null}
          <button type="button" onClick={() => window.print()} className="btn-ghost">
            <Printer className="h-4 w-4" />
            Print / PDF
          </button>
        </div>
      </div>

      <ScoreSummary report={report} />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Resume length" value={`${stats.word_count ?? 0} words`} hint={`${stats.pages ?? 1} page(s)`} />
        <Stat
          label="Quantified bullets"
          value={`${stats.bullets_with_metrics ?? 0}/${stats.bullet_count ?? 0}`}
          hint="lines containing a number"
        />
        <Stat
          label="Experience detected"
          value={stats.years_experience ? `${stats.years_experience} yrs` : "n/a"}
          hint="from dates and claims"
        />
        <Stat
          label="Skills recognised"
          value={stats.skills_detected?.length ?? 0}
          hint="matched against the ontology"
        />
      </div>

      <EvidenceList evidence={report.evidence} />
      <AtsPanel ats={report.ats} />
      <SuggestionsPanel suggestions={report.suggestions} />
      <PipelineFooter report={report} />

      {shared && shareUrl ? (
        <p className="no-print flex items-center gap-2 text-xs text-slate-600">
          <Link2 className="h-3.5 w-3.5" />
          Anyone with this link can view the report. No resume file is stored, only the analysis.
        </p>
      ) : null}
    </motion.div>
  );
}
