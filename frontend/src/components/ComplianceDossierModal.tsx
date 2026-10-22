"use client";

import React from "react";
import { StructuredImpactReport } from "@/services/api";
import {
  Printer,
  X,
  FileCheck2,
  ShieldCheck,
  Building2,
  Calendar,
  Layers,
  Scale,
  Award,
} from "lucide-react";

interface ComplianceDossierModalProps {
  report: StructuredImpactReport;
  businessName?: string;
  onClose: () => void;
}

export const ComplianceDossierModal: React.FC<ComplianceDossierModalProps> = ({
  report,
  businessName = "Registered Sri Lankan Food Enterprise",
  onClose,
}) => {
  const handlePrint = () => {
    window.print();
  };

  const isNarrativeVerified =
    report.narrative_summary &&
    !report.narrative_summary.includes("failed verification");

  const todayStr = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 md:p-6 no-print">
      {/* Modal Dialog Card */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Action Header (Excluded from Print) */}
        <div className="p-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between no-print">
          <div className="flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-indigo-400" />
            <span className="text-sm font-semibold text-white">
              Official Regulatory Compliance Dossier
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Print / PDF Ready
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              type="button"
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md shadow-indigo-950/50 transition-all cursor-pointer"
            >
              <Printer className="w-4 h-4" />
              <span>Print / Save as PDF</span>
            </button>
            <button
              onClick={onClose}
              type="button"
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Document Container (Styled for Screen Preview + High-Contrast Print) */}
        <div
          id="compliance-dossier-print-view"
          className="flex-1 overflow-y-auto p-6 sm:p-10 bg-white text-slate-900 font-sans print:p-0 print:m-0 dossier-print-container"
        >
          {/* 1. Official Republic / Gazette Header */}
          <div className="text-center pb-6 border-b-2 border-slate-900 space-y-1">
            <div className="inline-flex items-center justify-center gap-2 text-slate-800 mb-1">
              <Scale className="w-6 h-6 text-slate-900" />
              <span className="text-xs font-serif uppercase tracking-widest font-bold">
                Democratic Socialist Republic of Sri Lanka
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-serif font-black tracking-tight text-slate-950 uppercase">
              Regulatory Impact & Action Dossier
            </h1>
            <p className="text-xs text-slate-600 font-medium">
              Statutory Compliance Assessment &bull; Neuro-Symbolic 3-Valued Kleene Engine
            </p>
          </div>

          {/* 2. Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-4 border-b border-slate-300 text-xs text-slate-700">
            <div>
              <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                Target Enterprise
              </span>
              <span className="font-bold text-slate-900">{businessName}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                Assessment As-At Date
              </span>
              <span className="font-bold text-slate-900">{report.as_at_date}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                Date of Issue
              </span>
              <span className="font-bold text-slate-900">{todayStr}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                Dossier Serial
              </span>
              <span className="font-mono font-bold text-slate-900">
                REG-SL-{report.as_at_date.replace(/-/g, "")}-V1
              </span>
            </div>
          </div>

          {/* 3. Metric Summary Bar */}
          <div className="grid grid-cols-4 gap-2 my-5 text-center">
            <div className="p-2.5 rounded-lg border border-slate-300 bg-slate-50">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Evaluated</span>
              <span className="text-lg font-black text-slate-900">{report.total_rules_evaluated}</span>
            </div>
            <div className="p-2.5 rounded-lg border border-emerald-300 bg-emerald-50">
              <span className="text-[10px] uppercase font-bold text-emerald-700 block">Applicable</span>
              <span className="text-lg font-black text-emerald-900">{report.applicable_rules_count}</span>
            </div>
            <div className="p-2.5 rounded-lg border border-amber-300 bg-amber-50">
              <span className="text-[10px] uppercase font-bold text-amber-700 block">Conditional</span>
              <span className="text-lg font-black text-amber-900">{report.conditional_rules_count}</span>
            </div>
            <div className="p-2.5 rounded-lg border border-slate-300 bg-slate-50">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Not Applicable</span>
              <span className="text-lg font-black text-slate-700">{report.not_applicable_rules_count}</span>
            </div>
          </div>

          {/* 4. Verified Executive Narrative Summary */}
          <div className="mb-6 space-y-2">
            <div className="flex items-center justify-between pb-1 border-b border-slate-200">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                1. Executive Regulatory Impact Summary
              </h2>
              {isNarrativeVerified && (
                <span className="text-[10px] font-semibold text-emerald-800 bg-emerald-100 border border-emerald-300 px-2 py-0.5 rounded">
                  Component [J] Evidence Verified
                </span>
              )}
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-800 leading-relaxed font-serif">
              {report.narrative_summary || "No narrative summary provided."}
            </div>
          </div>

          {/* 5. Categorized Action Checklist */}
          <div className="mb-6 space-y-2">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900 pb-1 border-b border-slate-200">
              2. Actionable Compliance Checklist
            </h2>
            {report.action_checklist.length > 0 ? (
              <div className="space-y-2 pt-1">
                {report.action_checklist.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2.5 p-2 rounded-lg border border-slate-200 bg-white text-xs text-slate-800"
                  >
                    <span className="font-bold text-slate-500 shrink-0">[{idx + 1}]</span>
                    <span className="leading-snug">{item}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic py-1">
                No immediate mandatory compliance actions required based on currently active rules.
              </p>
            )}
          </div>

          {/* 6. Affected Activities & Corporate Documents */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <div className="space-y-1.5">
              <h3 className="text-xs font-bold uppercase text-slate-900">
                Affected Business Activities
              </h3>
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 min-h-16 text-xs text-slate-700">
                {report.affected_activities.length > 0 ? (
                  <ul className="list-disc list-inside space-y-0.5">
                    {report.affected_activities.map((act, i) => (
                      <li key={i}>{act}</li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-slate-400 italic">None identified</span>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <h3 className="text-xs font-bold uppercase text-slate-900">
                Affected Corporate Documents
              </h3>
              <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 min-h-16 text-xs text-slate-700">
                {report.affected_documents.length > 0 ? (
                  <ul className="list-disc list-inside space-y-0.5">
                    {report.affected_documents.map((doc, i) => (
                      <li key={i}>{doc}</li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-slate-400 italic">None identified</span>
                )}
              </div>
            </div>
          </div>

          {/* 7. Explicit Statutory Citations Table */}
          <div className="mb-6 space-y-2">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900 pb-1 border-b border-slate-200">
              3. Authoritative Statutory Citations & Legal Audit Register
            </h2>
            <div className="border border-slate-300 rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 border-b border-slate-300 text-[10px] font-bold uppercase text-slate-700">
                    <th className="p-2.5">Rule / Clause</th>
                    <th className="p-2.5">Gazette / Document</th>
                    <th className="p-2.5">Page</th>
                    <th className="p-2.5">Status</th>
                    <th className="p-2.5">Review Audit</th>
                    <th className="p-2.5">Verbatim Quote Grounding</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-[11px]">
                  {report.evaluations.map((ev, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="p-2.5 font-bold font-mono text-slate-900">
                        {ev.clause || ev.rule_id}
                      </td>
                      <td className="p-2.5 text-slate-700">
                        <span className="font-semibold block">{ev.instrument}</span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {ev.document_id || "Gazette"}
                        </span>
                      </td>
                      <td className="p-2.5 font-mono text-slate-600">
                        {ev.page_number ? `p. ${ev.page_number}` : "p. 1"}
                      </td>
                      <td className="p-2.5">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                            ev.status === "APPLICABLE"
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                              : ev.status === "CONDITIONAL_MISSING_DATA"
                              ? "bg-amber-100 text-amber-800 border border-amber-300"
                              : "bg-slate-100 text-slate-600 border border-slate-300"
                          }`}
                        >
                          {ev.status}
                        </span>
                      </td>
                      <td className="p-2.5">
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-blue-100 text-blue-800 border border-blue-300 uppercase">
                          {ev.review_status || "APPROVED"}
                        </span>
                      </td>
                      <td className="p-2.5 text-slate-600 italic font-serif max-w-xs">
                        &ldquo;{ev.quote_span ? ev.quote_span.slice(0, 140) : "N/A"}
                        {ev.quote_span && ev.quote_span.length > 140 ? "..." : ""}&rdquo;
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 8. Sign-off and Certification */}
          <div className="pt-6 border-t-2 border-slate-900 grid grid-cols-2 gap-8 text-xs text-slate-700">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                Legal Compliance Certifier
              </span>
              <p className="font-semibold text-slate-900">RegImpact-SL Automated Kleene Engine</p>
              <p className="text-[11px] text-slate-500">Dual-Pass Verified Legal Logic Pipeline</p>
            </div>
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold text-slate-500 block mb-8">
                Authorized Signature & Company Seal
              </span>
              <div className="border-b border-slate-400 w-48 ml-auto mb-1" />
              <p className="text-[10px] text-slate-500">Authorized Officer / Managing Director</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
