import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col items-start px-5 py-24">
      <p className="label">404</p>
      <h1 className="mt-3 text-3xl font-semibold text-white">Nothing here</h1>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-slate-400">
        This report link is invalid, or the analysis was run without saving. Reports are stored only
        when the API has a database configured.
      </p>
      <Link href="/" className="btn-primary mt-8">
        Run a new analysis
      </Link>
    </div>
  );
}
