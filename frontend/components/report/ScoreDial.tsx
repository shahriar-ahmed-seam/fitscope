"use client";

import { motion } from "framer-motion";

import { scoreTone } from "@/lib/format";

export function ScoreDial({
  score,
  label,
  size = 168,
  caption,
}: {
  score: number;
  label: string;
  size?: number;
  caption?: string;
}) {
  const tone = scoreTone(score);
  const stroke = size > 120 ? 11 : 8;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.max(0, Math.min(100, score)) / 100);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.07)"
            strokeWidth={stroke}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={tone.stroke}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.1, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={`font-mono ${size > 120 ? "text-4xl" : "text-2xl"} font-semibold ${tone.text}`}
          >
            {score.toFixed(0)}
          </span>
          <span className="mt-0.5 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            / 100
          </span>
        </div>
      </div>
      <p className="mt-3 text-sm font-medium text-white print-text">{label}</p>
      {caption ? <p className="mt-0.5 text-center text-xs text-slate-500">{caption}</p> : null}
    </div>
  );
}
