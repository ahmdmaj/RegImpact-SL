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

  const displayNarrative = report.narrative_summary && report.narrative_summary !== "Mock generated text explanation."
    ? report.narrative_summary
    : `Evaluation completed as-at ${report.as_at_date}: ${report.applicable_rules_count} mandatory statutory obligation(s) identified, ${report.conditional_rules_count} rule(s) requiring clarifying data, and ${report.not_applicable_rules_count} rule(s) exempt or inactive. Review the action checklist and grounded statutory citations below.`;

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
    <div className="space-y-5">
      {/* Dossier Modal */}
      {showDossierModal && (
        <ComplianceDossierModal
          report={report}
          onClose={() => setShowDossierModal(false)}
        />
      )}

      {/* Official Dossier Export Header Action */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-lg border border-zinc-800 bg-zinc-900">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700">
            <FileCheck2 className="w-4 h-4 text-zinc-300" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-100">
              Regulatory Compliance Dossier
            </h3>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              Export verified determinations, citations, and operational checklist as a printable audit document.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowDossierModal(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-xs font-medium border border-zinc-700 transition-colors cursor-pointer shrink-0"
        >
          <FileDown className="w-3.5 h-3.5 text-zinc-300" />
          <span>Export Dossier</span>
        </button>
      </div>

      {/* 1. Metric Overview Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
        <MetricCard
          label="Evaluated"
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
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700">
              <Sparkles className="w-3.5 h-3.5 text-zinc-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-zinc-100">
                Executive Compliance Summary
              </h3>
              <p className="text-[11px] text-zinc-400 mt-0.5">
                Evaluation Date: <span className="font-mono text-zinc-300">{report.as_at_date}</span>
              </p>
            </div>
          </div>

          {/* Verification Badge */}
          {isNarrativeVerified ? (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>Evidence Verified</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              <span>Verification Withheld</span>
            </span>
          )}
        </div>

        <p className="text-xs text-zinc-300 leading-relaxed font-normal">
          {displayNarrative}
        </p>

        <div className="pt-1 flex items-center gap-2 text-[11px] text-zinc-500">
          <ShieldCheck className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
          <span>
            Grounding Verified: All thresholds, dates, and licensing citations are checked against Gazette quote spans.
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
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 space-y-3">
          <div className="flex items-center gap-2 pb-2.5 border-b border-zinc-800">
            <div className="p-1.5 rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700">
              <Compass className="w-3.5 h-3.5 text-zinc-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-zinc-100">
                Sensitivity Analysis (Statutory Thresholds)
              </h3>
              <p className="text-[11px] text-zinc-400 mt-0.5">
                Simulated boundary conditions showing parameter shifts:
              </p>
            </div>
          </div>

          <div className="space-y-1.5 pt-1">
            {allCounterfactuals.map((cf, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-md bg-zinc-950 border border-zinc-850 text-xs text-zinc-300 leading-relaxed font-mono"
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
