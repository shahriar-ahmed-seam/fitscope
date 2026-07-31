"use client";

import { ArrowRight, Lightbulb, PlusCircle, Sparkles, Zap } from "lucide-react";

import type { Suggestions } from "@/lib/types";
import { CopyButton, SectionHeading } from "@/components/ui/Primitives";

export function SuggestionsPanel({ suggestions }: { suggestions: Suggestions }) {
  const { tailored_summary, rewrites, add_these, quick_wins, mode } = suggestions;
  const hasContent =
    tailored_summary || rewrites.length > 0 || add_these.length > 0 || quick_wins.length > 0;

  if (!hasContent) return null;

  return (
    <section>
      <SectionHeading
        eyebrow="Actionable edits"
        title="What to change"
        description={
          mode === "llm"
            ? "Rewrites are grounded in your own bullets. Placeholders like [X%] mark numbers only you can supply."
            : "Generated from deterministic rules because the language model was unavailable."
        }
      />

      {tailored_summary ? (
        <div className="panel-tight mb-3 p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="label flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              Tailored summary
            </p>
            <CopyButton text={tailored_summary} className="no-print" />
          </div>
          <p className="text-sm leading-relaxed text-slate-200 print-text">{tailored_summary}</p>
        </div>
      ) : null}

      {rewrites.length > 0 ? (
        <ul className="space-y-3">
          {rewrites.map((rewrite, index) => (
            <li key={`${rewrite.bullet_id ?? "rw"}-${index}`} className="panel-tight p-4">
              <div className="grid gap-3 md:grid-cols-[1fr,auto,1fr] md:items-center">
                <p className="text-sm leading-relaxed text-slate-500 line-through decoration-rose-500/40 print-text">
                  {rewrite.original}
                </p>
                <ArrowRight
                  className="hidden h-4 w-4 shrink-0 text-accent/60 md:block"
                  aria-hidden="true"
                />
                <p className="text-sm font-medium leading-relaxed text-slate-100 print-text">
                  {rewrite.rewritten}
                </p>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.05] pt-2.5">
                <p className="text-xs text-slate-500">
                  <Lightbulb className="mr-1.5 inline h-3.5 w-3.5 text-amber-400/70" />
                  {rewrite.reason}
                  {rewrite.targets.length > 0 ? (
                    <span className="ml-2 font-mono text-[11px] text-slate-600">
                      targets {rewrite.targets.join(", ")}
                    </span>
                  ) : null}
                </p>
                <CopyButton text={rewrite.rewritten} label="Copy line" className="no-print" />
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {add_these.length > 0 ? (
          <div className="panel-tight p-4">
            <p className="label mb-2.5 flex items-center gap-2">
              <PlusCircle className="h-3.5 w-3.5 text-sky-400" />
              Add to the resume
            </p>
            <ul className="space-y-2">
              {add_these.map((item) => (
                <li key={item} className="flex gap-2 text-sm leading-relaxed text-slate-300 print-text">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-sky-400" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {quick_wins.length > 0 ? (
          <div className="panel-tight p-4">
            <p className="label mb-2.5 flex items-center gap-2">
              <Zap className="h-3.5 w-3.5 text-amber-400" />
              Quick wins
            </p>
            <ul className="space-y-2">
              {quick_wins.map((item) => (
                <li key={item} className="flex gap-2 text-sm leading-relaxed text-slate-300 print-text">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-400" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}
