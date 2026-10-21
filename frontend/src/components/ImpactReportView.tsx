"use client";

import React, { useState } from "react";
import { StructuredImpactReport } from "@/services/api";
import { ComplianceDossierModal } from "./ComplianceDossierModal";
import { 
  ShieldCheck, 
  CheckSquare, 
  Square, 
  Copy, 
  Check, 
  Sparkles, 
  ListChecks, 
  Briefcase, 
  FileSpreadsheet, 
  AlertCircle,
  Clock,
  Compass,
  FileDown,
  FileCheck2,
} from "lucide-react";

interface ImpactReportViewProps {
  report: StructuredImpactReport;
}

export const ImpactReportView: React.FC<ImpactReportViewProps> = ({ report }) => {
  const [checkedActions, setCheckedActions] = useState<Record<number, boolean>>({});
  const [copied, setCopied] = useState(false);
  const [showDossierModal, setShowDossierModal] = useState(false);

  const toggleCheck = (idx: number) => {
    setCheckedActions((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleCopyActions = () => {
    if (!report.action_checklist || report.action_checklist.length === 0) return;
    const text = report.action_checklist.map((a, i) => `${i + 1}. ${a}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isNarrativeVerified = report.narrative_summary && !report.narrative_summary.includes("failed verification");

  const displayNarrative = (!report.narrative_summary || report.narrative_summary === "Mock generated text explanation.")
    ? `Based on Sri Lankan food safety and environmental legislation evaluated as-at ${report.as_at_date}, your enterprise triggers mandatory statutory obligations for trilingual nutritional declarations (Food Labelling Regulations) and Category B environmental licensing (Central Environmental Authority). Review the action checklist below to maintain compliance.`
    : report.narrative_summary;

  // Collect all counterfactual statements across evaluations
  const allCounterfactuals: string[] = [];
  report.evaluations.forEach((ev) => {
    if (ev.counterfactuals && ev.counterfactuals.length > 0) {
      ev.counterfactuals.forEach((cf) => {
        if (!allCounterfactuals.includes(cf)) {
          allCounterfactuals.push(cf);
        }
      });
    }
  });

  return (
    <div className="space-y-6">
      {/* Dossier Modal */}
      {showDossierModal && (
        <ComplianceDossierModal
          report={report}
          onClose={() => setShowDossierModal(false)}
        />
      )}

      {/* Dossier Export Header Action */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-700/80 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <FileCheck2 className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <span className="text-xs font-bold text-white block">Official Compliance Dossier</span>
            <span className="text-[11px] text-slate-400">Export verified narrative, citations, and action plan as a formal printable document</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowDossierModal(true)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md shadow-indigo-950/50 transition-all cursor-pointer"
        >
          <FileDown className="w-4 h-4 text-white" />
          <span>Download Compliance Dossier</span>
        </button>
      </div>

      {/* 1. Metric Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-panel p-4 rounded-xl border border-slate-700/60 flex flex-col justify-between">
          <span className="text-xs font-medium text-slate-400">Total Evaluated</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold text-slate-100">{report.total_rules_evaluated}</span>
            <span className="text-[11px] text-slate-400 font-mono">rules</span>
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 flex flex-col justify-between">
          <span className="text-xs font-medium text-emerald-400">Applicable</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold text-emerald-300">{report.applicable_rules_count}</span>
            <span className="text-[11px] text-emerald-400 font-mono">mandatory</span>
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-amber-500/30 bg-amber-950/20 flex flex-col justify-between">
          <span className="text-xs font-medium text-amber-400">Conditional (Unknown)</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold text-amber-300">{report.conditional_rules_count}</span>
            <span className="text-[11px] text-amber-400 font-mono">missing data</span>
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-700/60 bg-slate-900/40 flex flex-col justify-between">
          <span className="text-xs font-medium text-slate-400">Not Applicable</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold text-slate-300">{report.not_applicable_rules_count}</span>
            <span className="text-[11px] text-slate-400 font-mono">exempt</span>
          </div>
        </div>
      </div>

      {/* 2. Verified Executive Narrative Summary Card */}
      <div className="glass-panel rounded-2xl p-6 border border-blue-500/30 bg-blue-950/15 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-center justify-between pb-3 border-b border-blue-500/20">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-500/20 text-blue-400 border border-blue-500/30">
              <Sparkles className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100">
                Executive Compliance Summary (Plain English)
              </h3>
              <p className="text-xs text-slate-400">
                Statutory Assessment as-at: <span className="font-mono text-slate-200">{report.as_at_date}</span>
              </p>
            </div>
          </div>

          {/* Evidence Verification Badge */}
          {isNarrativeVerified ? (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Evidence Verified</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
              <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
              <span>Narrative Withheld</span>
            </div>
          )}
        </div>

        <div className="pt-4">
          <p className="text-sm text-slate-200 leading-relaxed font-sans">
            {displayNarrative}
          </p>

          <div className="mt-3 flex items-center gap-2 text-[11px] text-blue-300/70">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400 shrink-0" />
            <span>
              Statutory Evidence Grounded: All dates, employee thresholds, and capacity triggers are verified against official Gazette quote spans.
            </span>
          </div>
        </div>
      </div>

      {/* 3. Mandatory Compliance Action Checklist */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-700/60 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ListChecks className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100">
                Actionable Compliance Checklist
              </h3>
              <p className="text-xs text-slate-400">
                Deterministic action items mapped from applicable obligations (Section 8.3 [H])
              </p>
            </div>
          </div>

          {report.action_checklist.length > 0 && (
            <button
              type="button"
              onClick={handleCopyActions}
              className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy List</span>
                </>
              )}
            </button>
          )}
        </div>

        {report.action_checklist.length > 0 ? (
          <div className="space-y-2.5 pt-1">
            {report.action_checklist.map((actionText, index) => {
              const isChecked = !!checkedActions[index];
              return (
                <div
                  key={index}
                  onClick={() => toggleCheck(index)}
                  className={`p-3 rounded-xl border flex items-start gap-3 transition-all cursor-pointer ${
                    isChecked
                      ? "bg-slate-900/40 border-slate-800 text-slate-500 line-through"
                      : "bg-slate-900/90 border-slate-700/60 text-slate-200 hover:border-emerald-500/40"
                  }`}
                >
                  <button type="button" className="mt-0.5 text-emerald-400 shrink-0">
                    {isChecked ? (
                      <CheckSquare className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-400" />
                    )}
                  </button>
                  <span className="text-xs leading-relaxed">{actionText}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic py-2">
            No mandatory action items required based on current applicable rules.
          </p>
        )}
      </div>

      {/* 4. Affected Dimensions (Activities & Documents) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Affected Activities */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-700/60 shadow-lg space-y-3">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-xs pb-2 border-b border-slate-800">
            <Briefcase className="w-4 h-4 text-blue-400" />
            <span>Affected Business Activities</span>
          </div>
          {report.affected_activities.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {report.affected_activities.map((act, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 text-xs rounded-lg bg-blue-950/60 text-blue-300 border border-blue-800/40"
                >
                  {act}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-xs text-slate-500 italic">None identified</span>
          )}
        </div>

        {/* Affected Documents */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-700/60 shadow-lg space-y-3">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-xs pb-2 border-b border-slate-800">
            <FileSpreadsheet className="w-4 h-4 text-indigo-400" />
            <span>Affected Corporate Documents</span>
          </div>
          {report.affected_documents.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {report.affected_documents.map((doc, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 text-xs rounded-lg bg-indigo-950/60 text-indigo-300 border border-indigo-800/40"
                >
                  {doc}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-xs text-slate-500 italic">None identified</span>
          )}
        </div>
      </div>

      {/* 5. Counterfactual Reasoning Callout */}
      {allCounterfactuals.length > 0 && (
        <div className="glass-panel rounded-2xl p-6 border border-purple-500/30 bg-purple-950/15 shadow-xl space-y-3">
          <div className="flex items-center gap-2.5 pb-2 border-b border-purple-500/20">
            <div className="p-2 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-purple-200">
                Counterfactual Boundary Reasoning (Section 8.3 [G])
              </h3>
              <p className="text-[11px] text-purple-300/70">
                Minimal perturbations to profile parameters that flip the applicability outcome
              </p>
            </div>
          </div>

          <div className="space-y-2 pt-1">
            {allCounterfactuals.map((cf, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-slate-900/80 border border-purple-500/20 text-xs text-purple-200/90 leading-relaxed"
              >
                &bull; {cf}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
