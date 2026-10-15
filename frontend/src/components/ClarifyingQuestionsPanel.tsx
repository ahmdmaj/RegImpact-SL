"use client";

import React, { useState } from "react";
import { HelpCircle, AlertTriangle, ArrowRight, ShieldAlert, CheckCircle2 } from "lucide-react";

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
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submittedFields, setSubmittedFields] = useState<Set<string>>(new Set());

  if (!questions || questions.length === 0) {
    return null;
  }

  const handleInputChange = (field: string, val: string) => {
    setAnswers((prev) => ({ ...prev, [field]: val }));
  };

  const handleApplySingle = (field: string) => {
    const rawVal = answers[field];
    if (rawVal === undefined || rawVal.trim() === "") return;

    let parsedVal: unknown = rawVal;
    if (!isNaN(Number(rawVal))) {
      parsedVal = Number(rawVal);
    } else if (rawVal.toLowerCase() === "true") {
      parsedVal = true;
    } else if (rawVal.toLowerCase() === "false") {
      parsedVal = false;
    }

    if (onAnswerField) {
      onAnswerField(field, parsedVal);
    }
    setSubmittedFields((prev) => new Set(prev).add(field));
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-amber-500/40 bg-amber-950/20 shadow-2xl relative overflow-hidden">
      {/* Decorative background glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-start justify-between gap-4 pb-4 border-b border-amber-500/20">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-amber-200">
                Action Required: Clarifying Questions
              </h3>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {questions.length} Pending {questions.length === 1 ? "Field" : "Fields"}
              </span>
            </div>
            <p className="text-xs text-amber-300/80 mt-0.5">
              Three-Valued Kleene Logic: The engine refused to hallucinate and requires the following data to resolve applicability.
            </p>
          </div>
        </div>

        {onReevaluate && (
          <button
            type="button"
            onClick={onReevaluate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-md transition-all cursor-pointer"
          >
            <span>Re-evaluate</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Questions List */}
      <div className="space-y-3 pt-4">
        {questions.map((question, index) => {
          const field = missingFields[index] || `field_${index}`;
          const isSubmitted = submittedFields.has(field);

          return (
            <div
              key={index}
              className="p-4 rounded-xl bg-slate-900/80 border border-amber-500/20 flex flex-col md:flex-row md:items-center justify-between gap-3"
            >
              <div className="flex items-start gap-2.5 flex-1">
                <HelpCircle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-slate-200">{question}</p>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">Field Path: {field}</p>
                </div>
              </div>

              {/* Inline Answer Input */}
              <div className="flex items-center gap-2 shrink-0">
                {isSubmitted ? (
                  <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-950/60 px-3 py-1.5 rounded-lg border border-emerald-700/50">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Provided ({answers[field]})</span>
                  </div>
                ) : (
                  <>
                    <input
                      type="text"
                      placeholder="e.g. 75"
                      value={answers[field] || ""}
                      onChange={(e) => handleInputChange(field, e.target.value)}
                      className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-amber-500 w-28"
                    />
                    <button
                      type="button"
                      onClick={() => handleApplySingle(field)}
                      disabled={!answers[field] || answers[field].trim() === ""}
                      className="px-2.5 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
                    >
                      Apply
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-3 border-t border-amber-500/10 flex items-center gap-2 text-xs text-amber-300/70">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
        <span>
          RegImpact-SL strictly adheres to Section 8.3 [G]: Zero guessing on missing fields. Providing these inputs converts UNKNOWN to TRUE or FALSE.
        </span>
      </div>
    </div>
  );
};
