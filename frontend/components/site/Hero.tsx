import Image from "next/image";
import { FileSearch, Gauge, ListChecks } from "lucide-react";

const HERO_IMAGE =
  "https://images.pexels.com/photos/34803994/pexels-photo-34803994.jpeg?auto=compress&cs=tinysrgb&w=1920";

const POINTS = [
  {
    icon: ListChecks,
    title: "Evidence, not vibes",
    body: "Every requirement is labelled covered, partial or missing and cites the exact resume line behind the call.",
  },
  {
    icon: Gauge,
    title: "Two separate scores",
    body: "Semantic fit answers whether you are qualified. ATS readiness answers whether the document survives a parser.",
  },
  {
    icon: FileSearch,
    title: "Rewrites you can paste",
    body: "Weak bullets come back sharpened, grounded in your own text, with placeholders where only you know the number.",
  },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-white/[0.06]">
      <div className="absolute inset-0">
        <Image
          src={HERO_IMAGE}
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-cover opacity-[0.13]"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-ink-950/60 via-ink-950/85 to-ink-950" />
      </div>

      <div className="relative mx-auto w-full max-w-6xl px-5 pb-14 pt-16 sm:pt-20">
        <p className="label mb-4">Resume ↔ job description intelligence</p>
        <h1 className="max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight text-white sm:text-5xl">
          Find out exactly which requirements your resume{" "}
          <span className="text-accent">does not</span> evidence.
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-slate-400">
          Paste a resume and a job posting. FitScope breaks the posting into screenable requirements,
          retrieves the resume lines that speak to each one, and grades the match with the evidence
          shown next to it. No score without a citation.
        </p>

        <dl className="mt-10 grid gap-5 sm:grid-cols-3">
          {POINTS.map(({ icon: Icon, title, body }) => (
            <div key={title} className="panel p-5">
              <Icon className="h-5 w-5 text-accent" aria-hidden="true" />
              <dt className="mt-3 text-sm font-semibold text-white">{title}</dt>
              <dd className="mt-1.5 text-sm leading-relaxed text-slate-400">{body}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
