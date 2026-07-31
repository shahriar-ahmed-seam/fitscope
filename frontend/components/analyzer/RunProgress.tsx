"use client";

import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/components/ui/Primitives";

/** Approximate durations, only used to animate the stage list. */
const STAGES = [
  { label: "Parsing resume structure", ms: 900 },
  { label: "Extracting screenable requirements", ms: 4200 },
  { label: "Retrieving candidate evidence lines", ms: 2600 },
  { label: "Judging coverage against each requirement", ms: 5200 },
  { label: "Scoring ATS mechanics", ms: 700 },
  { label: "Drafting targeted rewrites", ms: 6000 },
];

export function RunProgress({ fastMode }: { fastMode: boolean }) {
  const stages = fastMode ? STAGES.slice(0, 5) : STAGES;
  const [active, setActive] = useState(0);

  useEffect(() => {
    let index = 0;
    const timers: number[] = [];
    const schedule = () => {
      if (index >= stages.length - 1) return;
      const timer = window.setTimeout(() => {
        index += 1;
        setActive(index);
        schedule();
      }, stages[index].ms);
      timers.push(timer);
    };
    schedule();
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [stages]);

  return (
    <div className="panel p-6">
      <div className="mb-5 flex items-center gap-2.5">
        <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden="true" />
        <p className="text-sm font-medium text-white">Analysing</p>
        <span className="ml-auto text-xs text-slate-500">
          typically 6-20 seconds{fastMode ? " · fast mode" : ""}
        </span>
      </div>

      <ol className="space-y-2.5" aria-live="polite">
        {stages.map((stage, index) => {
          const done = index < active;
          const current = index === active;
          return (
            <li key={stage.label} className="flex items-center gap-3">
              <span
                className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px]",
                  done
                    ? "border-accent/40 bg-accent/15 text-accent"
                    : current
                      ? "border-accent/40 bg-accent/10 text-accent"
                      : "border-white/10 text-slate-600",
                )}
              >
                {done ? (
                  <Check className="h-3 w-3" />
                ) : current ? (
                  <motion.span
                    className="h-1.5 w-1.5 rounded-full bg-accent"
                    animate={{ opacity: [1, 0.25, 1] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                  />
                ) : (
                  index + 1
                )}
              </span>
              <span
                className={cn(
                  "text-sm transition",
                  done ? "text-slate-500" : current ? "text-slate-100" : "text-slate-600",
                )}
              >
                {stage.label}
              </span>
            </li>
          );
        })}
      </ol>

      <div className="mt-5 h-1 overflow-hidden rounded-full bg-white/[0.06]">
        <motion.div
          className="h-full w-1/3 rounded-full bg-gradient-to-r from-transparent via-accent to-transparent"
          animate={{ x: ["-100%", "300%"] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "linear" }}
        />
      </div>
    </div>
  );
}
