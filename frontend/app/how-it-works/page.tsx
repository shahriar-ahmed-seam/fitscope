import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import { API_BASE } from "@/lib/api";

export const metadata: Metadata = {
  title: "How it works",
  description:
    "The retrieval, judging and scoring pipeline behind FitScope, the exact scoring weights, and the correlation against human labels.",
};

const SIDE_IMAGE =
  "https://images.pexels.com/photos/5668863/pexels-photo-5668863.jpeg?auto=compress&cs=tinysrgb&w=1280";

const STAGES = [
  {
    step: "01",
    title: "Structure the resume",
    body: "PDF and DOCX text is extracted, then split into sections and achievement lines with rules only. No model touches this stage, so the ATS score is reproducible across runs. Contact details, date ranges, metrics and skill mentions are detected here.",
  },
  {
    step: "02",
    title: "Break the posting into requirements",
    body: "The job description is decomposed into 8-18 atomic, screenable requirements, each tagged must-have, nice-to-have or responsibility, with the employer's own keywords preserved. A regex-based extractor takes over if the model is unavailable.",
  },
  {
    step: "03",
    title: "Retrieve candidate evidence",
    body: "Requirements and resume lines are embedded in a single batched request, and cosine similarity shortlists the most plausible lines per requirement. When the embedding quota is exhausted, an IDF-weighted lexical scorer takes over — recall over the requirement's informative terms, which stays comparable across queries.",
  },
  {
    step: "04",
    title: "Judge coverage, grounded",
    body: "One model call labels every requirement covered, partial or missing and must cite one of the shortlisted line ids. Because the citation is constrained to real ids, the evidence shown in the report cannot be fabricated. Coverage is never inferred from embedding cosine, which is not calibrated across queries.",
  },
  {
    step: "05",
    title: "Score mechanics separately",
    body: "Nine deterministic checks grade parseability, contact block, headings, dated history, quantification, action verbs, bullet length, keyword coverage and formatting hygiene. This score is independent of qualifications on purpose.",
  },
  {
    step: "06",
    title: "Draft grounded rewrites",
    body: "Weak bullets are rewritten against the gaps found in step 4, using only facts already present in the original line. Missing numbers become explicit placeholders rather than invented figures.",
  },
];

const METRICS = [
  { label: "Pearson r vs human labels", value: "0.996", hint: "semantic fit, 12 labelled pairs" },
  { label: "Spearman ρ vs human labels", value: "0.959", hint: "rank correlation" },
  { label: "Pairwise ranking accuracy", value: "89.2%", hint: "65 label-distinct comparisons" },
  { label: "Top-1 role match", value: "3/3", hint: "best job picked per resume" },
];

export default function HowItWorksPage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-14">
      <p className="label">Methodology</p>
      <h1 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
        A score is only useful if you can see why.
      </h1>
      <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-400">
        FitScope keeps the deterministic and the generative parts of the pipeline apart, so document
        mechanics stay reproducible and every qualitative judgement carries a citation you can check
        against your own resume.
      </p>

      <div className="mt-12 grid gap-10 lg:grid-cols-[1.6fr,1fr]">
        <ol className="space-y-4">
          {STAGES.map((stage) => (
            <li key={stage.step} className="panel flex gap-4 p-5">
              <span className="font-mono text-sm text-accent/70">{stage.step}</span>
              <div>
                <h2 className="text-sm font-semibold text-white">{stage.title}</h2>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{stage.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="space-y-6">
          <div className="panel overflow-hidden">
            <div className="relative h-40">
              <Image
                src={SIDE_IMAGE}
                alt="A candidate in a job interview across a desk from a recruiter"
                fill
                sizes="(max-width: 1024px) 100vw, 380px"
                className="object-cover opacity-70"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-ink-900 via-ink-900/40 to-transparent" />
            </div>
            <div className="p-5">
              <h2 className="text-sm font-semibold text-white">Measured, not asserted</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
                Twelve resume × job pairs were labelled 0-100 by hand before any model output was
                inspected, then scored by the live pipeline.
              </p>
              <dl className="mt-4 space-y-2.5">
                {METRICS.map((metric) => (
                  <div key={metric.label} className="flex items-baseline justify-between gap-3">
                    <dt className="text-xs text-slate-500">
                      {metric.label}
                      <span className="block text-[11px] text-slate-600">{metric.hint}</span>
                    </dt>
                    <dd className="font-mono text-sm text-accent">{metric.value}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 text-[11px] leading-relaxed text-slate-600">
                Reproduce with <code className="font-mono text-slate-500">python -m eval.run_eval</code>{" "}
                in the backend. A 12-pair set is small: treat these as a sanity check on ordering, not
                a benchmark.
              </p>
            </div>
          </div>

          <div className="panel p-5">
            <h2 className="text-sm font-semibold text-white">Weights are public</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
              Overall readiness is 65% semantic fit and 35% ATS readiness. Must-haves carry 3× the
              weight of nice-to-haves, responsibilities 1.5×. Covered counts 1.0, partial 0.5.
            </p>
            <a
              href={`${API_BASE}/api/v1/scoring`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-block text-xs font-medium text-accent underline-offset-4 hover:underline"
            >
              GET /api/v1/scoring →
            </a>
          </div>

          <div className="panel p-5">
            <h2 className="text-sm font-semibold text-white">Limits worth knowing</h2>
            <ul className="mt-2 space-y-2 text-sm leading-relaxed text-slate-400">
              <li>
                Scanned or image-only PDFs cannot be read — and real ATS parsers fail on them too,
                which is itself the finding.
              </li>
              <li>
                Judgements reflect what the resume states. A skill you have but never wrote down will
                read as missing.
              </li>
              <li>
                No employer&apos;s actual ATS is being queried. The mechanics score models common
                parser and screener behaviour, not one specific vendor.
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-12">
        <Link href="/" className="btn-primary">
          Analyse a resume
        </Link>
      </div>
    </div>
  );
}
