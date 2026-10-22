"use client";

import React, { useState } from "react";
import { RuleAnalysisDetail } from "@/services/api";
import { 
  ChevronDown, 
  ChevronUp, 
  CheckCircle2, 
  AlertCircle, 
  XCircle, 
  Code2, 
  FileText,
  Clock,
  ShieldCheck,
  Compass
} from "lucide-react";

interface StatutoryCitationCardProps {
  evaluation: RuleAnalysisDetail;
  defaultExpanded?: boolean;
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

export function formatGazetteTitle(title?: string | null, docId?: string | null): string {
  if (docId && CLEAN_DOCUMENT_TITLES[docId.toLowerCase()]) {
    return CLEAN_DOCUMENT_TITLES[docId.toLowerCase()];
  }
  if (!title) return "Official Sri Lankan Statutory Gazette";
  if (title.length > 30 && /^[a-fA-F0-9_]+$/.test(title.replace(/doc_/g, ""))) {
    const lower = title.toLowerCase();
    if (lower.includes("b78479b6")) return "Food (Flavouring Substances & Enhancers) Regulations 2013";
    if (lower.includes("3f85f3ef")) return "Food (Preservatives) Regulations 2019";
    return "Official Sri Lanka Gazette Extraordinary";
  }
  return title;
}

export const StatutoryCitationCard: React.FC<StatutoryCitationCardProps> = ({
  evaluation: ev,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [showTechnical, setShowTechnical] = useState(false);

  const isCoverageGap = ev.coverage_gap || ev.status === "UNSUPPORTED";
  const gazetteTitle = formatGazetteTitle(ev.document_title || ev.instrument, ev.document_id);

  // Status configuration
  const getStatusConfig = () => {
    if (isCoverageGap) {
      return {
        badge: "GAZETTE NOTICE",
        badgeStyle: "bg-sky-500/10 text-sky-400 border-sky-500/20",
        cardBorder: "border-sky-900/40",
        icon: null,
      };
    }
    if (ev.status === "APPLICABLE") {
      return {
        badge: "MANDATORY",
        badgeStyle: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
        cardBorder: "border-emerald-900/40",
        icon: CheckCircle2,
      };
    }
    if (ev.status === "CONDITIONAL_MISSING_DATA") {
      return {
        badge: "DATA NEEDED",
        badgeStyle: "bg-amber-500/10 text-amber-400 border-amber-500/20",
        cardBorder: "border-amber-900/40",
        icon: AlertCircle,
      };
    }
    return {
      badge: "EXEMPT",
      badgeStyle: "bg-slate-800 text-slate-400 border-slate-700",
      cardBorder: "border-slate-800",
      icon: XCircle,
    };
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  return (
    <div className={`rounded-xl border ${statusConfig.cardBorder} bg-slate-900 overflow-hidden transition-all shadow-sm`}>
      {/* Clickable Header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between gap-3 text-left hover:bg-slate-800/40 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-3 flex-wrap">
          {/* Status Badge */}
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusConfig.badgeStyle}`}>
            {StatusIcon && <StatusIcon className="w-3.5 h-3.5" />}
            <span>{statusConfig.badge}</span>
          </span>

          {/* Clause & Document */}
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-white">
                {ev.clause}
              </span>
              <span className="text-xs text-slate-400">
                &bull; {gazetteTitle}
              </span>
              {ev.review_status && ev.review_status.includes("APPROVED") && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                  Certified
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Authority: <span className="text-slate-300">{ev.authority || "Sri Lanka Statutory Authority"}</span>
            </p>
          </div>
        </div>

        <div className="text-slate-400">
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="p-4 pt-2 border-t border-slate-800 space-y-3.5 bg-slate-950/30">
          {/* Notice for coverage gaps */}
          {isCoverageGap && (
            <div className="p-3 rounded-lg bg-sky-950/30 border border-sky-800/30 text-xs text-sky-200/90 leading-relaxed">
              <span className="font-semibold text-sky-300 block mb-0.5">Statutory Ingestion Notice:</span>
              This clause was indexed directly from official Gazettes as relevant to food businesses, and is awaiting formal reviewer sign-off in the Reviewer Portal. The engine abstains from creating obligations until certified.
            </div>
          )}

          {/* Verbatim Gazette Quote in Distinct Serif */}
          {ev.quote_span && (
            <div className="space-y-1">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Official Gazette Text (Verbatim Excerpt)
              </span>
              <div className="p-3.5 rounded-lg bg-[#080d16] border-l-2 border-slate-600 border-r border-t border-b border-slate-800 text-xs text-slate-200 legal-quote-text italic">
                &ldquo;{ev.quote_span}&rdquo;
              </div>
            </div>
          )}

          {/* Engine Reason & Temporal Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-0.5 font-medium">Evaluation Verdict:</span>
              <span className="text-slate-200 leading-relaxed">{ev.reason || "Evaluated by deterministic Kleene logic."}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-0.5 font-medium">Statutory Enforcement:</span>
              <span className="text-slate-200 font-mono text-[11px]">{ev.temporal_status || "Active & In Effect"}</span>
            </div>
          </div>

          {/* Collapsible Technical Details / Provenance Accordion */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setShowTechnical(!showTechnical)}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>{showTechnical ? "Hide Technical Audit Data" : "Inspect Technical Audit Data & Trace"}</span>
            </button>

            {showTechnical && (
              <div className="mt-2 p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] space-y-2">
                <div className="grid grid-cols-2 gap-2 text-slate-400">
                  <div>Rule ID: <span className="text-slate-200">{ev.rule_id}</span></div>
                  <div>Page No: <span className="text-slate-200">{ev.page_number ?? 1}</span></div>
                  <div>Char Offsets: <span className="text-slate-200">[{ev.char_start ?? 0} &ndash; {ev.char_end ?? 0}]</span></div>
                  <div>Review Status: <span className="text-slate-200">{ev.review_status || "APPROVED"}</span></div>
                </div>

                {ev.evaluation_trace && ev.evaluation_trace.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-slate-800">
                    <span className="text-slate-400 block mb-1">Kleene Evaluation Trace:</span>
                    <pre className="p-2 rounded bg-[#060a12] text-slate-300 text-[10px] overflow-x-auto max-h-40">
                      {JSON.stringify(ev.evaluation_trace, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
