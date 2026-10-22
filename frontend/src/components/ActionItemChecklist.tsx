"use client";

import React, { useState } from "react";
import { 
  CheckSquare, 
  Square, 
  Copy, 
  Check, 
  ListChecks, 
  Clock, 
  Briefcase 
} from "lucide-react";

interface ActionItemChecklistProps {
  actionChecklist: string[];
  affectedActivities?: string[];
  affectedDocuments?: string[];
}

export const ActionItemChecklist: React.FC<ActionItemChecklistProps> = ({
  actionChecklist,
  affectedActivities = [],
  affectedDocuments = [],
}) => {
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({});
  const [copied, setCopied] = useState(false);

  const toggleCheck = (idx: number) => {
    setCheckedItems((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const completedCount = Object.values(checkedItems).filter(Boolean).length;
  const totalCount = actionChecklist.length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const handleCopy = () => {
    if (actionChecklist.length === 0) return;
    const text = actionChecklist.map((a, i) => `${i + 1}. ${a}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (actionChecklist.length === 0) {
    return (
      <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/60 text-center">
        <p className="text-sm text-slate-400">
          No immediate statutory compliance action items triggered for the current profile parameters.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 shadow-sm p-6 space-y-5">
      {/* Header & Copy Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white">
              Compliance Action Checklist
            </h3>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {completedCount}/{totalCount} Completed
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Prioritized operational, licensing, and labelling tasks derived from verified statutory rules.
          </p>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 transition-colors self-start sm:self-auto cursor-pointer"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? "Copied" : "Copy Checklist"}</span>
        </button>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>Action Item Completion</span>
          <span className="font-mono text-slate-300">{progressPercent}%</span>
        </div>
        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Checklist Items */}
      <div className="space-y-2">
        {actionChecklist.map((action, idx) => {
          const isDone = !!checkedItems[idx];
          return (
            <div
              key={idx}
              onClick={() => toggleCheck(idx)}
              className={`p-3.5 rounded-lg border text-xs transition-all cursor-pointer flex items-start gap-3 select-none ${
                isDone
                  ? "bg-slate-950/60 border-slate-800/80 text-slate-500 line-through"
                  : "bg-slate-950/40 border-slate-800 text-slate-200 hover:bg-slate-800/40"
              }`}
            >
              <button
                type="button"
                className="mt-0.5 text-slate-400 hover:text-white shrink-0 focus:outline-none"
              >
                {isDone ? (
                  <CheckSquare className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-500" />
                )}
              </button>
              <div className="flex-1 leading-relaxed">
                <span className="font-mono text-[11px] text-slate-500 mr-2">
                  #{idx + 1}
                </span>
                <span>{action}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Affected Activities & Documents Badges */}
      {(affectedActivities.length > 0 || affectedDocuments.length > 0) && (
        <div className="pt-4 border-t border-slate-800 flex flex-wrap gap-4 text-xs text-slate-400">
          {affectedActivities.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-medium">Affected Activities:</span>
              <div className="flex flex-wrap gap-1">
                {affectedActivities.map((act) => (
                  <span
                    key={act}
                    className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700/60"
                  >
                    {act}
                  </span>
                ))}
              </div>
            </div>
          )}

          {affectedDocuments.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-medium">Required Documents:</span>
              <div className="flex flex-wrap gap-1">
                {affectedDocuments.map((doc) => (
                  <span
                    key={doc}
                    className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700/60"
                  >
                    {doc}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
