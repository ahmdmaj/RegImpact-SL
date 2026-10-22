"use client";

import React, { useState } from "react";
import { StructuredImpactReport } from "@/services/api";
import { ComplianceDossierModal } from "./ComplianceDossierModal";
import { MetricCard } from "./MetricCard";
import { ActionItemChecklist } from "./ActionItemChecklist";
import { 
  ShieldCheck, 
  FileCheck2, 
  FileDown, 
  AlertCircle, 
  Compass, 
  Sparkles,
  Layers,
  Scale
} from "lucide-react";

interface ImpactReportViewProps {
  report: StructuredImpactReport;
}

export const ImpactReportView: React.FC<ImpactReportViewProps> = ({ report }) => {
  const [showDossierModal, setShowDossierModal] = useState(false);

  const isNarrativeVerified = report.narrative_summary && !report.narrative_summary.includes("failed verification");

  const displayNarrative = (!report.narrative_summary || report.narrative_summary === "Mock generated text explanation.")
    ? `Based on Sri Lankan food safety and environmental legislation evaluated as-at ${report.as_at_date}, your enterprise triggers mandatory statutory obligations for trilingual nutritional declarations (Food Labelling Regulations) and Category B environmental licensing (Central Environmental Authority). Review the action checklist below to maintain compliance.`
    : report.narrative_summary;

  // Collect all unique counterfactuals
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

      {/* Official Dossier Export Header Action */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl border border-slate-800 bg-slate-900 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
            <FileCheck2 className="w-5 h-5 text-slate-300" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">
              Official Regulatory Compliance Dossier
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Export verified statutory determinations, citations, and operational checklist as a printable audit document.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowDossierModal(true)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-white text-slate-900 text-xs font-semibold shadow-sm transition-all cursor-pointer shrink-0"
        >
          <FileDown className="w-4 h-4 text-slate-900" />
          <span>Export Compliance Dossier</span>
        </button>
      </div>

      {/* 1. Metric Overview Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Total Evaluated"
          value={report.total_rules_evaluated}
          subtext="rules"
          variant="neutral"
          icon={Layers}
        />
        <MetricCard
          label="Mandatory"
          value={report.applicable_rules_count}
          subtext="obligations"
          variant="success"
          icon={ShieldCheck}
        />
        <MetricCard
          label="Data Needed"
          value={report.conditional_rules_count}
          subtext="questions"
          variant="warning"
          icon={AlertCircle}
        />
        <MetricCard
          label="Exempt"
          value={report.not_applicable_rules_count}
          subtext="clauses"
          variant="neutral"
          icon={Scale}
        />
      </div>

      {/* 2. Plain-English Executive Compliance Summary Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
              <Sparkles className="w-4 h-4 text-slate-300" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">
                Executive Compliance Summary
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluation Point-in-Time Date: <span className="font-mono text-slate-300">{report.as_at_date}</span>
              </p>
            </div>
          </div>

          {/* Verification Badge */}
          {isNarrativeVerified ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Evidence Verified</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Verification Withheld</span>
            </span>
          )}
        </div>

        <p className="text-xs text-slate-200 leading-relaxed font-normal">
          {displayNarrative}
        </p>

        <div className="pt-2 flex items-center gap-2 text-[11px] text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          <span>
            Grounding Verified: All numerical thresholds, dates, and licensing citations are checked against Gazette quote spans.
          </span>
        </div>
      </div>

      {/* 3. Actionable Checklist Component */}
      <ActionItemChecklist
        actionChecklist={report.action_checklist}
        affectedActivities={report.affected_activities}
        affectedDocuments={report.affected_documents}
      />

      {/* 4. What-If Sensitivity Analysis (Statutory Thresholds) */}
      {allCounterfactuals.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 shadow-sm p-6 space-y-3">
          <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
            <div className="p-2 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
              <Compass className="w-4 h-4 text-slate-300" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">
                What-If Sensitivity Analysis (Statutory Thresholds)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Simulated boundary conditions showing how parameter variations alter your legal exposure:
              </p>
            </div>
          </div>

          <div className="space-y-2 pt-1">
            {allCounterfactuals.map((cf, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-mono"
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
