import { AnalyzerPanel } from "@/components/analyzer/AnalyzerPanel";
import { Hero } from "@/components/site/Hero";
import { RecentRuns } from "@/components/site/RecentRuns";

export default function HomePage() {
  return (
    <>
      <Hero />
      <div className="mx-auto w-full max-w-6xl space-y-10 px-5 py-12">
        <AnalyzerPanel />
        <RecentRuns />
      </div>
    </>
  );
}
