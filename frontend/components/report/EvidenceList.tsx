"use client";

import { motion } from "framer-motion";
import { Quote, ScanSearch } from "lucide-react";
import { useMemo, useState } from "react";

import {
  CATEGORY_LABELS,
  CATEGORY_STYLES,
  COVERAGE_STYLES,
  sectionLabel,
} from "@/lib/format";
import type { Coverage, Evidence } from "@/lib/types";
import { Chip, SectionHeading, cn } from "@/components/ui/Primitives";

type Filter = "all" | Coverage;

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "missing", label: "Missing" },
  { id: "partial", label: "Partial" },
  { id: "covered", label: "Covered" },
];

const ORDER: Record<Coverage, number> = { missing: 0, partial: 1, covered: 2 };

function EvidenceCard({ item, index }: { item: Evidence; index: number }) {
  const style = COVERAGE_STYLES[item.coverage];

  return (
    <motion.li
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.03, 0.3) }}
      className="panel-tight p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-xl text-sm font-medium leading-relaxed text-slate-100 print-text">
          {item.requirement.text}
        </p>
        <div className="flex flex-wrap items-center gap-1.5">
          <Chip className={CATEGORY_STYLES[item.requirement.category]}>
            {CATEGORY_LABELS[item.requirement.category]}
          </Chip>
          <Chip className={style.chip}>
            <span className={cn("h-1.5 w-1.5 rounded-full", style.dot)} />
            {style.label}
          </Chip>
        </div>
      </div>

      {item.best_bullet_text ? (
        <figure className="mt-3 rounded-lg border-l-2 border-accent/40 bg-white/[0.02] px-3.5 py-2.5">
          <div className="flex gap-2">
            <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent/60" aria-hidden="true" />
            <blockquote className="text-sm leading-relaxed text-slate-300 print-text">
              {item.best_bullet_text}
            </blockquote>
          </div>
          <figcaption className="mt-1.5 pl-5 text-[11px] uppercase tracking-wider text-slate-600">
            from {sectionLabel(item.best_bullet_section)}
            {item.supporting_bullet_ids.length > 0
              ? ` · +${item.supporting_bullet_ids.length} supporting line${
                  item.supporting_bullet_ids.length > 1 ? "s" : ""
                }`
              : ""}
          </figcaption>
        </figure>
      ) : (
        <p className="mt-3 rounded-lg border border-dashed border-rose-500/20 bg-rose-500/[0.04] px-3.5 py-2.5 text-sm text-rose-200/80 print-text">
          No line in the resume evidences this.
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-500">
        {item.justification ? (
          <span className="text-slate-400 print-text">{item.justification}</span>
        ) : null}
        {item.keyword_misses.length > 0 ? (
          <span>
            absent terms:{" "}
            <span className="font-mono text-rose-300/80">
              {item.keyword_misses.slice(0, 6).join(", ")}
            </span>
          </span>
        ) : null}
        <span className="ml-auto font-mono text-[11px] text-slate-600">
          {item.decided_by === "judge" ? "judged" : item.decided_by} · relevance{" "}
          {item.score.toFixed(2)}
          {item.confidence !== null ? ` · conf ${item.confidence.toFixed(2)}` : ""}
        </span>
      </div>
    </motion.li>
  );
}

export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  const [filter, setFilter] = useState<Filter>("all");

  const counts = useMemo(() => {
    return evidence.reduce<Record<string, number>>((acc, item) => {
      acc[item.coverage] = (acc[item.coverage] ?? 0) + 1;
      return acc;
    }, {});
  }, [evidence]);

  const visible = useMemo(() => {
    const list = filter === "all" ? [...evidence] : evidence.filter((e) => e.coverage === filter);
    return list.sort((a, b) => {
      const byCoverage = ORDER[a.coverage] - ORDER[b.coverage];
      if (byCoverage !== 0) return byCoverage;
      const weight = { must_have: 0, responsibility: 1, nice_to_have: 2 } as const;
      return weight[a.requirement.category] - weight[b.requirement.category];
    });
  }, [evidence, filter]);

  return (
    <section>
      <SectionHeading
        eyebrow="Requirement by requirement"
        title="Evidence table"
        description="Each requirement extracted from the job description, matched against the exact resume line that supports it. Gaps first."
        right={
          <div className="no-print flex flex-wrap gap-1.5" role="group" aria-label="Filter by coverage">
            {FILTERS.map((option) => {
              const active = filter === option.id;
              const count = option.id === "all" ? evidence.length : counts[option.id] ?? 0;
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setFilter(option.id)}
                  aria-pressed={active}
                  className={cn(
                    "rounded-lg border px-2.5 py-1.5 text-xs font-medium transition",
                    active
                      ? "border-accent/40 bg-accent/10 text-accent"
                      : "border-white/10 text-slate-400 hover:border-white/25 hover:text-white",
                  )}
                >
                  {option.label}
                  <span className="ml-1.5 font-mono text-[11px] opacity-70">{count}</span>
                </button>
              );
            })}
          </div>
        }
      />

      {visible.length === 0 ? (
        <div className="panel-tight flex items-center gap-3 px-4 py-6 text-sm text-slate-400">
          <ScanSearch className="h-4 w-4" />
          Nothing in this bucket.
        </div>
      ) : (
        <ul className="space-y-3">
          {visible.map((item, index) => (
            <EvidenceCard key={item.requirement.id} item={item} index={index} />
          ))}
        </ul>
      )}
    </section>
  );
}
