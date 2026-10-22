"use client";

import React, { useState } from "react";
import { RuleAnalysisDetail } from "@/services/api";
import { 
  ChevronDown, 
  ChevronUp, 
  Code2, 
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

  // Status configuration with minimal dots instead of loud colored blocks
  const getStatusConfig = () => {
    if (isCoverageGap) {
      return {
        badge: "GAZETTE NOTICE",
        dotColor: "bg-zinc-400",
      };
    }
    if (ev.status === "APPLICABLE") {
      return {
        badge: "MANDATORY",
        dotColor: "bg-emerald-400",
      };
    }
    if (ev.status === "CONDITIONAL_MISSING_DATA") {
      return {
        badge: "DATA NEEDED",
        dotColor: "bg-amber-400",
      };
    }
    return {
      badge: "EXEMPT",
      dotColor: "bg-zinc-500",
    };
  };

  const statusConfig = getStatusConfig();

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 overflow-hidden transition-colors">
      {/* Clickable Header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3.5 flex items-center justify-between gap-3 text-left hover:bg-zinc-850/50 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Subtle Status Badge */}
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-800 text-[10px] font-mono font-medium text-zinc-300 border border-zinc-700">
            <span className={`w-1.5 h-1.5 rounded-full ${statusConfig.dotColor}`} />
            <span>{statusConfig.badge}</span>
          </span>

          {/* Clause & Document */}
          <div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold text-zinc-100">
                {ev.clause}
              </span>
              <span className="text-[11px] text-zinc-400">
                &bull; {gazetteTitle}
              </span>
              {ev.review_status && ev.review_status.includes("APPROVED") && (
                <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                  Certified
                </span>
              )}
            </div>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Authority: <span className="text-zinc-400">{ev.authority || "Sri Lanka Statutory Authority"}</span>
            </p>
          </div>
        </div>

        <div className="text-zinc-500">
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="p-3.5 pt-1 border-t border-zinc-800/80 space-y-3 bg-zinc-950/40">
          {/* Notice for coverage gaps */}
          {isCoverageGap && (
            <div className="p-2.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 leading-relaxed">
              <span className="font-semibold text-zinc-200 block mb-0.5 text-[11px]">Corpus Notice:</span>
              This clause was indexed from official Gazettes and is pending formal reviewer sign-off in the Reviewer Portal. The engine abstains from creating obligations until certified.
            </div>
          )}

          {/* Verbatim Gazette Quote in Distinct Serif */}
          {ev.quote_span && (
            <div className="space-y-1">
              <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block">
                Gazette Excerpt (Verbatim)
              </span>
              <div className="p-3 rounded-md bg-zinc-950 border-l-2 border-zinc-600 border-r border-t border-b border-zinc-800 text-xs text-zinc-300 legal-quote-text italic">
                &ldquo;{ev.quote_span}&rdquo;
              </div>
            </div>
          )}

          {/* Engine Reason & Temporal Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <div className="p-2 rounded-md bg-zinc-900 border border-zinc-800">
              <span className="text-zinc-500 block text-[10px] uppercase font-mono mb-0.5">Verdict Reason:</span>
              <span className="text-zinc-300 leading-relaxed text-[11px]">{ev.reason || "Evaluated by deterministic Kleene logic."}</span>
            </div>
            <div className="p-2 rounded-md bg-zinc-900 border border-zinc-800">
              <span className="text-zinc-500 block text-[10px] uppercase font-mono mb-0.5">Enforcement Window:</span>
              <span className="text-zinc-300 font-mono text-[11px]">{ev.temporal_status || "Active & In Effect"}</span>
            </div>
          </div>

          {/* Collapsible Technical Details / Provenance Accordion */}
          <div className="pt-1">
            <button
              type="button"
              onClick={() => setShowTechnical(!showTechnical)}
              className="flex items-center gap-1.5 text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
            >
              <Code2 className="w-3 h-3" />
              <span>{showTechnical ? "Hide Audit Data" : "Inspect Technical Audit Data & Trace"}</span>
            </button>

            {showTechnical && (
              <div className="mt-2 p-2.5 rounded-md bg-zinc-950 border border-zinc-800 font-mono text-[11px] space-y-1.5">
                <div className="grid grid-cols-2 gap-1.5 text-zinc-500">
                  <div>Rule ID: <span className="text-zinc-300">{ev.rule_id}</span></div>
                  <div>Page No: <span className="text-zinc-300">{ev.page_number ?? 1}</span></div>
                  <div>Offsets: <span className="text-zinc-300">[{ev.char_start ?? 0} &ndash; {ev.char_end ?? 0}]</span></div>
                  <div>Review: <span className="text-zinc-300">{ev.review_status || "APPROVED"}</span></div>
                </div>

                {ev.evaluation_trace && ev.evaluation_trace.length > 0 && (
                  <div className="mt-1.5 pt-1.5 border-t border-zinc-800">
                    <span className="text-zinc-500 block mb-1">Kleene Evaluation Trace:</span>
                    <pre className="p-2 rounded bg-zinc-900 text-zinc-300 text-[10px] overflow-x-auto max-h-40">
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
