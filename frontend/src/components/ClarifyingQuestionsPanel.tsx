"use client";

import React, { useState } from "react";
import { HelpCircle, ArrowRight, CheckCircle2 } from "lucide-react";

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
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-800">
        <div className="flex items-start sm:items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700 shrink-0">
            <HelpCircle className="w-4 h-4 text-zinc-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-zinc-100">
                Optional Regulatory Clarifications
              </h3>
              <span className="px-1.5 py-0.2 text-[10px] font-mono rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                {questions.length} Pending
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              Primary food safety rules are evaluated. Provide these details to resolve secondary environmental conditions.
            </p>
          </div>
        </div>

        {onReevaluate && (
          <button
            type="button"
            onClick={onReevaluate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-medium transition-colors cursor-pointer shrink-0 self-start sm:self-center"
          >
            <span>Update Evaluation</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Questions List */}
      <div className="space-y-2.5">
        {questions.map((question, index) => {
          const field = missingFields[index] || `field_${index}`;
          const isSubmitted = submittedFields.has(field);
          const currentVal = answers[field];

          return (
            <div
              key={index}
              className={`p-3 rounded-md border transition-colors ${
                isSubmitted
                  ? "bg-zinc-950 border-zinc-700"
                  : "bg-zinc-950/60 border-zinc-800 hover:border-zinc-750"
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-0.5 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono uppercase text-zinc-400">
                      {getFriendlyFieldLabel(field)}
                    </span>
                    {isSubmitted && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-zinc-300 bg-zinc-800 border border-zinc-700 px-1.5 py-0.2 rounded font-mono">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        Provided: {String(currentVal)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-200 leading-relaxed">{question}</p>
                </div>

                {/* Controls */}
                <div className="flex items-center gap-2 flex-wrap shrink-0">
                  {field === "uses_synthetic_colorings" ? (
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, false)}
                        className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
                          currentVal === false
                            ? "bg-zinc-800 text-white border-zinc-600"
                            : "bg-zinc-900 text-zinc-300 border-zinc-800 hover:bg-zinc-800"
                        }`}
                      >
                        No (None)
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, true)}
                        className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
                          currentVal === true
                            ? "bg-zinc-800 text-white border-zinc-600"
                            : "bg-zinc-900 text-zinc-300 border-zinc-800 hover:bg-zinc-800"
                        }`}
                      >
                        Yes (Synthetic)
                      </button>
                    </div>
                  ) : field === "hazardous_chemicals_storage_liters" ? (
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, 0)}
                        className="px-2 py-1 rounded-md bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs border border-zinc-800 cursor-pointer"
                      >
                        0 Liters
                      </button>
                      <input
                        type="number"
                        placeholder="Liters"
                        value={currentVal !== undefined && currentVal !== 0 ? currentVal : ""}
                        onChange={(e) => setAnswers((prev) => ({ ...prev, [field]: e.target.value }))}
                        className="w-20 h-7 px-2 bg-zinc-900 border border-zinc-800 rounded-md text-xs text-white focus:outline-none focus:border-zinc-500"
                      />
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, Number(answers[field] || 0))}
                        className="px-2 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium border border-zinc-700 cursor-pointer"
                      >
                        Apply
                      </button>
                    </div>
                  ) : field === "wastewater_discharge_m3_per_day" ? (
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, 0)}
                        className="px-2 py-1 rounded-md bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs border border-zinc-800 cursor-pointer"
                      >
                        0 m³
                      </button>
                      <input
                        type="number"
                        placeholder="m³/day"
                        value={currentVal !== undefined && currentVal !== 0 ? currentVal : ""}
                        onChange={(e) => setAnswers((prev) => ({ ...prev, [field]: e.target.value }))}
                        className="w-20 h-7 px-2 bg-zinc-900 border border-zinc-800 rounded-md text-xs text-white focus:outline-none focus:border-zinc-500"
                      />
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, Number(answers[field] || 0))}
                        className="px-2 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium border border-zinc-700 cursor-pointer"
                      >
                        Apply
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5">
                      <input
                        type="text"
                        placeholder="Enter value..."
                        value={currentVal !== undefined ? currentVal : ""}
                        onChange={(e) => setAnswers((prev) => ({ ...prev, [field]: e.target.value }))}
                        className="w-28 h-7 px-2 bg-zinc-900 border border-zinc-800 rounded-md text-xs text-white focus:outline-none focus:border-zinc-500"
                      />
                      <button
                        type="button"
                        onClick={() => handleApplyValue(field, answers[field])}
                        className="px-2 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium border border-zinc-700 cursor-pointer"
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
