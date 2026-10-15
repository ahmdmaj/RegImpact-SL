"use client";

import React, { useState } from "react";
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
  ExternalLink,
  Layers
} from "lucide-react";

interface EvidenceViewerProps {
  evaluations: RuleAnalysisDetail[];
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ evaluations }) => {
  const [expandedRules, setExpandedRules] = useState<Record<string, boolean>>(() => {
    // Expand applicable and conditional rules by default
    const initial: Record<string, boolean> = {};
    evaluations.forEach((ev) => {
      if (ev.status === "APPLICABLE" || ev.status === "CONDITIONAL_MISSING_DATA") {
        initial[ev.rule_id] = true;
      }
    });
    return initial;
  });

  const toggleExpand = (ruleId: string) => {
    setExpandedRules((prev) => ({ ...prev, [ruleId]: !prev[ruleId] }));
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPLICABLE":
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>APPLICABLE</span>
          </span>
        );
      case "CONDITIONAL_MISSING_DATA":
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>CONDITIONAL (UNKNOWN)</span>
          </span>
        );
      case "NOT_APPLICABLE":
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-700/50 text-slate-300 border border-slate-600/40">
            <XCircle className="w-3.5 h-3.5" />
            <span>NOT APPLICABLE</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
            {status}
          </span>
        );
    }
  };

  const getTraceResultBadge = (res: string) => {
    switch (res) {
      case "TRUE":
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-700/50">TRUE</span>;
      case "FALSE":
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-400 border border-rose-700/50">FALSE</span>;
      case "UNKNOWN":
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-700/50">UNKNOWN</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">{res}</span>;
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-700/60 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-700/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <span>Statutory Evidence & Trace Audit</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {evaluations.length} Clauses Evaluated
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Section 8.3 [E & J]: Authoritative source is always the official gazette quote span, never the model.
            </p>
          </div>
        </div>
      </div>

      {/* Rules Accordion / Cards */}
      <div className="space-y-4">
        {evaluations.map((ev) => {
          const isExpanded = !!expandedRules[ev.rule_id];

          return (
            <div
              key={ev.rule_id}
              className={`rounded-xl border transition-all ${
                ev.status === "APPLICABLE"
                  ? "bg-slate-900/90 border-emerald-500/30 shadow-lg shadow-emerald-950/20"
                  : ev.status === "CONDITIONAL_MISSING_DATA"
                  ? "bg-slate-900/90 border-amber-500/30"
                  : "bg-slate-900/60 border-slate-700/50"
              }`}
            >
              {/* Card Header (clickable to expand) */}
              <button
                type="button"
                onClick={() => toggleExpand(ev.rule_id)}
                className="w-full p-4 flex items-center justify-between gap-3 text-left cursor-pointer hover:bg-slate-800/40 rounded-xl transition-colors"
              >
                <div className="flex items-center gap-3 flex-wrap">
                  {getStatusBadge(ev.status)}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-200">{ev.clause}</span>
                      <span className="text-xs text-slate-400 font-mono">({ev.rule_id})</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {ev.instrument} &bull; <span className="text-blue-400">{ev.authority}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {ev.temporal_status && (
                    <span className="hidden md:flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {ev.temporal_status}
                    </span>
                  )}
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Card Body */}
              {isExpanded && (
                <div className="p-4 pt-2 border-t border-slate-800 space-y-4">
                  {/* Official Gazette Quote Span */}
                  {ev.quote_span && (
                    <div>
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-1.5">
                        <FileText className="w-3.5 h-3.5 text-blue-400" />
                        <span>Official Grounding Excerpt (Quote Span):</span>
                      </div>
                      <blockquote className="p-3 rounded-lg bg-slate-950/80 border-l-4 border-blue-500 text-xs text-slate-300 italic font-serif leading-relaxed">
                        &ldquo;{ev.quote_span}&rdquo;
                      </blockquote>
                    </div>
                  )}

                  {/* 3-Valued Condition Trace Table */}
                  {ev.evaluation_trace && ev.evaluation_trace.length > 0 && (
                    <div>
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-1.5">
                        <Layers className="w-3.5 h-3.5 text-indigo-400" />
                        <span>Deterministic Condition Trace:</span>
                      </div>
                      <div className="overflow-x-auto rounded-lg border border-slate-800">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
                            <tr>
                              <th className="px-3 py-2">Profile Field</th>
                              <th className="px-3 py-2">Target Threshold</th>
                              <th className="px-3 py-2">Observed Value</th>
                              <th className="px-3 py-2 text-right">3-Valued Logic</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 font-mono">
                            {ev.evaluation_trace.map((tr, trIdx) => (
                              <tr key={trIdx} className="hover:bg-slate-800/30">
                                <td className="px-3 py-2 text-slate-300">{tr.field}</td>
                                <td className="px-3 py-2 text-slate-400">
                                  {typeof tr.target_value === "boolean"
                                    ? String(tr.target_value)
                                    : String(tr.target_value ?? "—")}
                                </td>
                                <td className="px-3 py-2 text-slate-200">
                                  {tr.observed_value === null || tr.observed_value === undefined ? (
                                    <span className="text-amber-400 italic font-sans text-[11px]">None (Unknown)</span>
                                  ) : typeof tr.observed_value === "boolean" ? (
                                    String(tr.observed_value)
                                  ) : (
                                    String(tr.observed_value)
                                  )}
                                </td>
                                <td className="px-3 py-2 text-right">
                                  {getTraceResultBadge(tr.result)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Counterfactual Guidance */}
                  {ev.counterfactuals && ev.counterfactuals.length > 0 && (
                    <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-700/30">
                      <div className="text-xs font-semibold text-indigo-300 mb-1">
                        Counterfactual Boundary Reasoning:
                      </div>
                      <ul className="list-disc list-inside text-xs text-indigo-200/90 space-y-0.5">
                        {ev.counterfactuals.map((cf, cfIdx) => (
                          <li key={cfIdx}>{cf}</li>
                        ))}
                      </ul>
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
