"use client";

import React, { useState, useMemo } from "react";
import { RuleAnalysisDetail } from "@/services/api";
import { StatutoryCitationCard } from "./StatutoryCitationCard";
import { 
  ShieldCheck, 
  Filter,
  Layers
} from "lucide-react";

interface EvidenceViewerProps {
  evaluations: RuleAnalysisDetail[];
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ evaluations }) => {
  const [filter, setFilter] = useState<"ALL" | "APPLICABLE" | "CONDITIONAL" | "EXEMPT" | "COVERAGE_GAP">("ALL");

  // Filtered list
  const filteredEvaluations = useMemo(() => {
    if (filter === "ALL") return evaluations;
    if (filter === "APPLICABLE") return evaluations.filter((e) => e.status === "APPLICABLE");
    if (filter === "CONDITIONAL") return evaluations.filter((e) => e.status === "CONDITIONAL_MISSING_DATA");
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
      else if (e.status === "CONDITIONAL_MISSING_DATA") cond++;
      else if (e.status === "NOT_APPLICABLE") exempt++;
    });
    return { app, cond, exempt, gap, total: evaluations.length };
  }, [evaluations]);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 shadow-sm p-6 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
            <ShieldCheck className="w-4 h-4 text-slate-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">
                Statutory Evidence & Legal Audit Citations
              </h3>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {counts.total} Total
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic provenance grounded in verbatim Sri Lankan Gazette quote spans with zero LLM hallucinations.
            </p>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={() => setFilter("ALL")}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "ALL"
                ? "bg-slate-100 text-slate-900 font-semibold"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            All ({counts.total})
          </button>
          <button
            type="button"
            onClick={() => setFilter("APPLICABLE")}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "APPLICABLE"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                : "bg-slate-800/80 text-emerald-400/90 hover:bg-slate-800"
            }`}
          >
            Mandatory ({counts.app})
          </button>
          <button
            type="button"
            onClick={() => setFilter("CONDITIONAL")}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "CONDITIONAL"
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                : "bg-slate-800/80 text-amber-400/90 hover:bg-slate-800"
            }`}
          >
            Data Needed ({counts.cond})
          </button>
          <button
            type="button"
            onClick={() => setFilter("EXEMPT")}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "EXEMPT"
                ? "bg-slate-700 text-white font-semibold"
                : "bg-slate-800/80 text-slate-400 hover:bg-slate-800"
            }`}
          >
            Exempt ({counts.exempt})
          </button>
          <button
            type="button"
            onClick={() => setFilter("COVERAGE_GAP")}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "COVERAGE_GAP"
                ? "bg-sky-500/20 text-sky-300 border border-sky-500/30"
                : "bg-slate-800/80 text-sky-400/90 hover:bg-slate-800"
            }`}
          >
            Gazette Notices ({counts.gap})
          </button>
        </div>
      </div>

      {/* Rules Citation List */}
      <div className="space-y-3">
        {filteredEvaluations.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 border border-slate-800 rounded-lg">
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
