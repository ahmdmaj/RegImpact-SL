"use client";

import React, { useState } from "react";
import { HelpCircle, Sparkles, ArrowRight, CheckCircle2, RotateCcw, Info } from "lucide-react";

interface ClarifyingQuestionsPanelProps {
  questions: string[];
  missingFields: string[];
  onAnswerField?: (field: string, value: unknown) => void;
  onReevaluate?: () => void;
}

export const ClarifyingQuestionsPanel: React.FC<ClarifyingQuestionsPanelProps> = ({
  questions,
  missingFields,
  onAnswerField,
  onReevaluate,
}) => {
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [submittedFields, setSubmittedFields] = useState<Set<string>>(new Set());

  if (!questions || questions.length === 0) {
    return null;
  }

  const handleApplyValue = (field: string, parsedVal: any) => {
    setAnswers((prev) => ({ ...prev, [field]: parsedVal }));
    if (onAnswerField) {
      onAnswerField(field, parsedVal);
    }
    setSubmittedFields((prev) => new Set(prev).add(field));
  };

  const getFriendlyFieldLabel = (field: string): string => {
    switch (field) {
      case "uses_synthetic_colorings":
        return "Synthetic Food Colorings";
      case "hazardous_chemicals_storage_liters":
        return "Hazardous Chemical Storage";
      case "wastewater_discharge_m3_per_day":
        return "Daily Wastewater Discharge";
      case "industry_category":
        return "Industrial EPL Classification";
      case "production_capacity.kg_per_day":
      case "production_capacity.value":
        return "Daily Production Capacity";
      case "employee_count":
        return "Total Employee Count";
      default:
        return field.replace(".", " ").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }
  };

  return (
    <div className="rounded-2xl p-6 border border-slate-700/80 bg-slate-900/90 shadow-xl relative overflow-hidden space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div className="flex items-start sm:items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
            <HelpCircle className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white">
                Optional Regulatory Clarifications
              </h3>
              <span className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {questions.length} Pending
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Your primary food manufacturing rules are evaluated. Answer these optional details to check secondary environmental and additive rules.
            </p>
          </div>
        </div>

        {onReevaluate && (
          <button
            type="button"
            onClick={onReevaluate}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md transition-all cursor-pointer shrink-0 self-start sm:self-center"
          >
            <span>Update Report</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Questions List */}
      <div className="space-y-3 pt-1">
        {questions.map((question, index) => {
          const field = missingFields[index] || `field_${index}`;
          const isSubmitted = submittedFields.has(field);
          const currentVal = answers[field];

          return (
            <div
              key={index}
              className={`p-4 rounded-xl border transition-all ${
                isSubmitted
                  ? "bg-slate-950/80 border-emerald-500/30"
                  : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400/90 font-mono">
                      {getFriendlyFieldLabel(field)}
                    </span>
                    {isSubmitted && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-700/50 px-1.5 py-0.2 rounded font-medium">
                        <CheckCircle2 className="w-3 h-3" />
                        Saved: {String(currentVal)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-200 leading-snug">{question}</p>
                </div>

                {/* Specialized Input Controls */}
                <div className="flex items-center gap-2 flex-wrap shrink-0">
                  {/* Case 1: Boolean Toggle for synthetic colorings */}
                  {field === "uses_synthetic_colorings" ? (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, false)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                          currentVal === false
                            ? "bg-emerald-600 text-white border-emerald-500"
                            : "bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800"
                        }`}
                      >
                        No (None Used)
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, true)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                          currentVal === true
                            ? "bg-amber-600 text-white border-amber-500"
                            : "bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800"
                        }`}
                      >
                        Yes (Synthetic Colors)
                      </button>
                    </div>
                  ) : field === "hazardous_chemicals_storage_liters" ? (
                    /* Case 2: Chemical storage volume */
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, 0)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs border border-slate-700 cursor-pointer"
                      >
                        0 Liters (None)
                      </button>
                      <input
                        type="number"
                        placeholder="Liters (e.g. 100)"
                        value={currentVal !== undefined && currentVal !== 0 ? currentVal : ""}
                        onChange={(e) => setAnswers((prev) => ({ ...prev, [field]: e.target.value }))}
                        className="w-28 px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, Number(answers[field] || 0))}
                        className="px-2.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium cursor-pointer"
                      >
                        Apply
                      </button>
                    </div>
                  ) : field === "wastewater_discharge_m3_per_day" ? (
                    /* Case 3: Wastewater volume */
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, 0)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs border border-slate-700 cursor-pointer"
                      >
                        0 m³ (None)
                      </button>
                      <input
                        type="number"
                        placeholder="m³/day"
                        value={currentVal !== undefined && currentVal !== 0 ? currentVal : ""}
                        onChange={(e) => setAnswers((prev) => ({ ...prev, [field]: e.target.value }))}
                        className="w-24 px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, Number(answers[field] || 0))}
                        className="px-2.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium cursor-pointer"
                      >
                        Apply
                      </button>
                    </div>
                  ) : field === "industry_category" ? (
                    /* Case 4: Category Dropdown */
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, "General Food Processing")}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs border border-slate-700 cursor-pointer"
                      >
                        General SME
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, "Part A")}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs border border-slate-700 cursor-pointer"
                      >
                        Part A
                      </button>
                    </div>
                  ) : (
                    /* Fallback General Input */
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="Enter value..."
                        value={currentVal !== undefined ? currentVal : ""}
                        onChange={(e) => setAnswers((prev) => ({ ...prev, [field]: e.target.value }))}
                        className="w-32 px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, answers[field])}
                        className="px-2.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium cursor-pointer"
                      >
                        Apply
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
