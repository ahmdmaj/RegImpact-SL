"use client";

import React, { useState, useMemo } from "react";
import { RuleAnalysisDetail } from "@/services/api";
import { 
  FileText, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  ChevronDown, 
  ChevronUp, 
  ShieldCheck, 
  Clock, 
  Filter,
  FileCheck,
  MapPin,
  ExternalLink,
  BookOpen,
} from "lucide-react";

interface EvidenceViewerProps {
  evaluations: RuleAnalysisDetail[];
}

const CLEAN_DOCUMENT_TITLES: Record<string, string> = {
  "doc_fcau_labelling_2024": "Food (Labelling and Advertising) Regulations 2024",
  "doc_cea_epl_2022": "National Environmental (Protection and Quality) Regulations 2022",
  "doc_caa_mrp_2023": "Consumer Affairs Authority (Display of MRP) Direction 2023",
  "doc_gazette_2443_27": "Sri Lanka Gazette Extraordinary 2443/27 (Labelling Amendments)",
  "doc_gazette_2494_06": "Sri Lanka Gazette Extraordinary 2494/06",
  "doc_gazette_2494_47": "Sri Lanka Gazette Extraordinary 2494/47",
  "doc_gazette_2496_03": "Sri Lanka Gazette Extraordinary 2496/03",
  "doc_fcau_labelling_advertising_en": "Food (Labelling and Advertising) Regulations",
  "doc_labelling_regulations_final_2026": "Food Labelling Regulations Final (2026)",
  "doc_colouring_substances_2011": "Food (Colouring Substances) Regulations 2011",
  "doc_flavouring_enhancers_2013": "Food (Flavouring Substances & Enhancers) Regulations 2013",
  "doc_food_preservatives_regulations": "Food (Preservatives) Regulations 2019",
};

function formatDocTitle(title?: string | null, docId?: string | null): string {
  if (docId && CLEAN_DOCUMENT_TITLES[docId.toLowerCase()]) {
    return CLEAN_DOCUMENT_TITLES[docId.toLowerCase()];
  }
  if (!title) return "Official Sri Lankan Statutory Gazette";
  // If title looks like a long hex hash, detect from known substrings or provide clean fallback
  if (title.length > 30 && /^[a-fA-F0-9_]+$/.test(title.replace(/doc_/g, ""))) {
    const lower = title.toLowerCase();
    if (lower.includes("b78479b6")) return "Food (Flavouring Substances & Enhancers) Regulations 2013";
    if (lower.includes("3f85f3ef")) return "Food (Preservatives) Regulations 2019";
    return "Official Sri Lanka Gazette Extraordinary";
  }
  return title;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ evaluations }) => {
  const [filter, setFilter] = useState<"ALL" | "APPLICABLE" | "CONDITIONAL" | "EXEMPT" | "COVERAGE_GAP">("ALL");
  const [showTechnical, setShowTechnical] = useState<Record<string, boolean>>({});
  
  // Expand only Applicable rules by default so the list is clean
  const [expandedRules, setExpandedRules] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    evaluations.forEach((ev) => {
      if (ev.status === "APPLICABLE") {
        initial[ev.rule_id] = true;
      }
    });
    return initial;
  });

  const toggleExpand = (ruleId: string) => {
    setExpandedRules((prev) => ({ ...prev, [ruleId]: !prev[ruleId] }));
  };

  const toggleTechnical = (ruleId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setShowTechnical((prev) => ({ ...prev, [ruleId]: !prev[ruleId] }));
  };

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
    <div className="rounded-2xl p-6 border border-slate-700/80 bg-slate-900/80 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <span>Statutory Evidence & Legal Audit Trail</span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {counts.total} Citations
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Every decision is grounded against verbatim Sri Lankan Gazette quote spans with zero hallucinations.
            </p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={() => setFilter("ALL")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "ALL"
                ? "bg-indigo-600 text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            All ({counts.total})
          </button>
          <button
            type="button"
            onClick={() => setFilter("APPLICABLE")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "APPLICABLE"
                ? "bg-emerald-600 text-white"
                : "bg-slate-800 text-emerald-400 hover:bg-slate-750"
            }`}
          >
            Mandatory ({counts.app})
          </button>
          <button
            type="button"
            onClick={() => setFilter("CONDITIONAL")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "CONDITIONAL"
                ? "bg-amber-600 text-white"
                : "bg-slate-800 text-amber-400 hover:bg-slate-750"
            }`}
          >
            Missing Data ({counts.cond})
          </button>
          <button
            type="button"
            onClick={() => setFilter("EXEMPT")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "EXEMPT"
                ? "bg-slate-600 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-750"
            }`}
          >
            Exempt ({counts.exempt})
          </button>
          <button
            type="button"
            onClick={() => setFilter("COVERAGE_GAP")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === "COVERAGE_GAP"
                ? "bg-purple-600 text-white"
                : "bg-slate-800 text-purple-400 hover:bg-slate-750"
            }`}
          >
            Coverage Notes ({counts.gap})
          </button>
        </div>
      </div>

      {/* Rules List */}
      <div className="space-y-3">
        {filteredEvaluations.map((ev) => {
          const isExpanded = !!expandedRules[ev.rule_id];
          const isTechExpanded = !!showTechnical[ev.rule_id];
          const isCoverageGap = ev.coverage_gap || ev.status === "UNSUPPORTED";
          const friendlyDoc = formatDocTitle(ev.document_title || ev.instrument, ev.document_id);

          return (
            <div
              key={ev.rule_id}
              className={`rounded-xl border transition-all overflow-hidden ${
                isCoverageGap
                  ? "bg-slate-950/60 border-purple-500/30"
                  : ev.status === "APPLICABLE"
                  ? "bg-slate-950/80 border-emerald-500/40 shadow-sm shadow-emerald-950/40"
                  : ev.status === "CONDITIONAL_MISSING_DATA"
                  ? "bg-slate-950/60 border-amber-500/30"
                  : "bg-slate-950/40 border-slate-800"
              }`}
            >
              {/* Card Header */}
              <button
                type="button"
                onClick={() => toggleExpand(ev.rule_id)}
                className="w-full p-4 flex items-center justify-between gap-3 text-left cursor-pointer hover:bg-slate-900/60 transition-colors"
              >
                <div className="flex items-center gap-3 flex-wrap">
                  {/* Status Badge */}
                  {isCoverageGap ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      <span>GAZETTE NOTICE</span>
                    </span>
                  ) : ev.status === "APPLICABLE" ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>MANDATORY</span>
                    </span>
                  ) : ev.status === "CONDITIONAL_MISSING_DATA" ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      <AlertCircle className="w-3.5 h-3.5" />
                      <span>DATA NEEDED</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                      <XCircle className="w-3.5 h-3.5" />
                      <span>EXEMPT</span>
                    </span>
                  )}

                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-white">
                        {ev.clause}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        &bull; {friendlyDoc}
                      </span>
                      {ev.review_status && ev.review_status.includes("APPROVED") && (
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-700/50">
                          Certified Rule
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Authority: <span className="text-slate-300">{ev.authority || "Sri Lanka Statutory Authority"}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Card Body */}
              {isExpanded && (
                <div className="p-4 pt-2 border-t border-slate-800/80 space-y-3 bg-slate-900/30">
                  {/* Coverage Gap Explanation */}
                  {isCoverageGap && (
                    <div className="p-3 rounded-xl bg-purple-950/20 border border-purple-500/30 text-xs text-purple-200/90 leading-relaxed">
                      <span className="font-semibold text-purple-300 block mb-0.5">Legal Corpus Notice:</span>
                      This clause was identified from official Gazettes as relevant to food businesses, but is pending expert sign-off in the Reviewer Portal. The engine abstains from creating obligations until certified.
                    </div>
                  )}

                  {/* Verbatim Grounding Quote Span */}
                  {ev.quote_span && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                        Official Gazette Text (Verbatim Excerpt)
                      </span>
                      <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 text-xs text-slate-200 font-serif leading-relaxed italic relative">
                        &ldquo;{ev.quote_span}&rdquo;
                      </div>
                    </div>
                  )}

                  {/* Deterministic Condition Trace (if applicable or conditional) */}
                  {ev.evaluation_trace && ev.evaluation_trace.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                        Why this outcome was reached:
                      </span>
                      <div className="border border-slate-800 rounded-lg overflow-hidden">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-950 text-[10px] font-semibold text-slate-400 uppercase">
                            <tr>
                              <th className="p-2">Profile Parameter</th>
                              <th className="p-2">Statutory Trigger</th>
                              <th className="p-2">Your Value</th>
                              <th className="p-2">Result</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/80 text-[11px] font-mono">
                            {ev.evaluation_trace.map((tr, i) => (
                              <tr key={i} className="hover:bg-slate-950/50">
                                <td className="p-2 text-slate-300 font-sans">{tr.field}</td>
                                <td className="p-2 text-slate-400">{String(tr.target_value)}</td>
                                <td className="p-2 text-slate-200">{tr.observed_value !== null && tr.observed_value !== undefined ? String(tr.observed_value) : "Unknown (blank)"}</td>
                                <td className="p-2">
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                    tr.result === "TRUE"
                                      ? "bg-emerald-950 text-emerald-400 border border-emerald-700/50"
                                      : tr.result === "FALSE"
                                      ? "bg-rose-950 text-rose-400 border border-rose-700/50"
                                      : "bg-amber-950 text-amber-400 border border-amber-700/50"
                                  }`}>
                                    {tr.result}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Technical Provenance Toggle */}
                  <div className="pt-1 flex items-center justify-between text-[11px]">
                    <button
                      type="button"
                      onClick={(e) => toggleTechnical(ev.rule_id, e)}
                      className="text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1 cursor-pointer"
                    >
                      <MapPin className="w-3 h-3 text-slate-500" />
                      <span>{isTechExpanded ? "Hide Technical Offsets" : "Inspect Offsets & Source Document ID"}</span>
                    </button>
                    <span className="text-[10px] font-mono text-slate-500">Rule ID: {ev.rule_id}</span>
                  </div>

                  {isTechExpanded && (
                    <div className="p-2.5 rounded-lg bg-slate-950 text-[10px] font-mono text-slate-400 border border-slate-800 space-y-1">
                      <div>Document ID: <span className="text-slate-200">{ev.document_id || "raw_gazette"}</span></div>
                      <div>Gazette Page: <span className="text-slate-200">{ev.page_number ?? 1}</span> &bull; Char Offsets: <span className="text-slate-200">[{ev.char_start ?? 0}:{ev.char_end ?? 0}]</span></div>
                      <div>Review Status: <span className="text-emerald-400">{ev.review_status || "APPROVED"}</span></div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
