"use client";

import React, { useState, useMemo } from "react";
import { RuleAnalysisDetail } from "@/services/api";
import { StatutoryCitationCard } from "./StatutoryCitationCard";
import { ShieldCheck } from "lucide-react";

interface EvidenceViewerProps {
  evaluations: RuleAnalysisDetail[];
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ evaluations }) => {
  const [filter, setFilter] = useState<"ALL" | "APPLICABLE" | "CONDITIONAL" | "EXEMPT" | "COVERAGE_GAP">("ALL");

  // Filtered list
  const filteredEvaluations = useMemo(() => {
    if (filter === "ALL") return evaluations;
    if (filter === "APPLICABLE") return evaluations.filter((e) => e.status === "APPLICABLE");
    if (filter === "CONDITIONAL") return evaluations.filter((e) => e.status === "CONDITIONAL_MISSING_DATA" || e.status === "CONDITIONAL_RULE");
    if (filter === "EXEMPT") return evaluations.filter((e) => e.status === "NOT_APPLICABLE");
    if (filter === "COVERAGE_GAP") return evaluations.filter((e) => e.coverage_gap || e.status === "UNSUPPORTED");
    return evaluations;
  }, [evaluations, filter]);

  // Counts
  const counts = useMemo(() => {
    let app = 0, cond = 0, exempt = 0, gap = 0;
    evaluations.forEach((e) => {
      if (e.coverage_gap || e.status === "UNSUPPORTED") gap++;
      else if (e.status === "APPLICABLE") app++;
      else if (e.status === "CONDITIONAL_MISSING_DATA" || e.status === "CONDITIONAL_RULE") cond++;
      else if (e.status === "NOT_APPLICABLE") exempt++;
    });
    return { app, cond, exempt, gap, total: evaluations.length };
  }, [evaluations]);

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-800">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700">
            <ShieldCheck className="w-4 h-4 text-zinc-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-zinc-100">
                Statutory Evidence & Legal Audit Citations
              </h3>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                {counts.total} Citations
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              Grounded against verbatim Sri Lankan Gazette quote spans with zero hallucinations.
            </p>
          </div>
        </div>

        {/* Filter Toolbar: Vercel/Linear Minimalist Segmented Buttons */}
        <div className="flex items-center gap-1 flex-wrap">
          <button
            type="button"
            onClick={() => setFilter("ALL")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              filter === "ALL"
                ? "bg-zinc-800 text-white border border-zinc-700"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            All ({counts.total})
          </button>
          <button
            type="button"
            onClick={() => setFilter("APPLICABLE")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
              filter === "APPLICABLE"
                ? "bg-zinc-800 text-white border border-zinc-700"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Mandatory ({counts.app})</span>
          </button>
          <button
            type="button"
            onClick={() => setFilter("CONDITIONAL")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
              filter === "CONDITIONAL"
                ? "bg-zinc-800 text-white border border-zinc-700"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>Missing Data ({counts.cond})</span>
          </button>
          <button
            type="button"
            onClick={() => setFilter("EXEMPT")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
              filter === "EXEMPT"
                ? "bg-zinc-800 text-white border border-zinc-700"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
            <span>Exempt ({counts.exempt})</span>
          </button>
          <button
            type="button"
            onClick={() => setFilter("COVERAGE_GAP")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
              filter === "COVERAGE_GAP"
                ? "bg-zinc-800 text-white border border-zinc-700"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
            <span>Notices ({counts.gap})</span>
          </button>
        </div>
      </div>

      {/* Rules Citation List */}
      <div className="space-y-2.5">
        {filteredEvaluations.length === 0 ? (
          <div className="p-8 text-center text-xs text-zinc-500 border border-zinc-800 rounded-md">
            No statutory citations found for the selected filter.
          </div>
        ) : (
          filteredEvaluations.map((ev) => (
            <StatutoryCitationCard
              key={ev.rule_id}
              evaluation={ev}
              defaultExpanded={ev.status === "APPLICABLE"}
            />
          ))
        )}
      </div>
    </div>
  );
};
