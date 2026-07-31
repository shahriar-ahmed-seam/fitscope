import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { fetchReportServerSide } from "@/lib/api";
import { ReportView } from "@/components/report/ReportView";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const report = await fetchReportServerSide(id);
  if (!report) return { title: "Report not found" };

  const role = report.job.role_title ?? "role";
  return {
    title: `${role} — ${report.scores.overall.toFixed(0)}/100 fit`,
    description: `${report.scores.verdict}: ${report.scores.covered} requirements covered, ${report.scores.missing} missing. Semantic fit ${report.scores.semantic_fit}/100, ATS readiness ${report.scores.ats_readiness}/100.`,
    robots: { index: false, follow: false },
  };
}

export default async function SharedReportPage({ params }: PageProps) {
  const { id } = await params;
  const report = await fetchReportServerSide(id);

  if (!report) notFound();

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-12">
      <div className="no-print mb-6">
        <Link href="/" className="text-xs text-slate-500 transition hover:text-accent">
          ← Run your own analysis
        </Link>
        <h1 className="mt-3 text-2xl font-semibold text-white">
          {report.job.role_title ?? "Fit report"}
          {report.job.company ? (
            <span className="text-slate-500"> · {report.job.company}</span>
          ) : null}
        </h1>
      </div>
      <ReportView report={report} shared />
    </div>
  );
}
