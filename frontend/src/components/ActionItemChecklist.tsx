"use client";

import React, { useState } from "react";
import { 
  CheckSquare, 
  Square, 
  Copy, 
  Check, 
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
      <div className="p-6 rounded-lg border border-zinc-800 bg-zinc-900 text-center">
        <p className="text-xs text-zinc-400">
          No immediate statutory compliance action items triggered for the current profile parameters.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 space-y-4">
      {/* Header & Copy Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-semibold text-zinc-100">
              Compliance Action Checklist
            </h3>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
              {completedCount}/{totalCount} Completed
            </span>
          </div>
          <p className="text-[11px] text-zinc-400 mt-0.5">
            Operational tasks derived from verified statutory rules.
          </p>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-zinc-800 text-zinc-300 hover:text-white hover:bg-zinc-750 border border-zinc-700 transition-colors self-start sm:self-auto cursor-pointer"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-zinc-200" /> : <Copy className="w-3.5 h-3.5 text-zinc-400" />}
          <span>{copied ? "Copied" : "Copy List"}</span>
        </button>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[11px] text-zinc-400">
          <span>Completion Progress</span>
          <span className="font-mono text-zinc-300">{progressPercent}%</span>
        </div>
        <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-zinc-200 transition-all duration-300 rounded-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Checklist Items */}
      <div className="space-y-1.5">
        {actionChecklist.map((action, idx) => {
          const isDone = !!checkedItems[idx];
          return (
            <div
              key={idx}
              onClick={() => toggleCheck(idx)}
              className={`p-2.5 rounded-md border text-xs transition-colors cursor-pointer flex items-start gap-2.5 select-none ${
                isDone
                  ? "bg-zinc-950/40 border-zinc-850 text-zinc-500 line-through"
                  : "bg-zinc-950/80 border-zinc-800/80 text-zinc-200 hover:border-zinc-700"
              }`}
            >
              <button
                type="button"
                className="mt-0.5 text-zinc-400 hover:text-zinc-200 shrink-0 focus:outline-none"
              >
                {isDone ? (
                  <CheckSquare className="w-3.5 h-3.5 text-zinc-300" />
                ) : (
                  <Square className="w-3.5 h-3.5 text-zinc-600" />
                )}
              </button>
              <div className="flex-1 leading-relaxed">
                <span className="font-mono text-[10px] text-zinc-500 mr-2">
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
        <div className="pt-3 border-t border-zinc-800 flex flex-wrap gap-4 text-xs text-zinc-400">
          {affectedActivities.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-500 font-mono text-[11px]">Activities:</span>
              <div className="flex flex-wrap gap-1">
                {affectedActivities.map((act) => (
                  <span
                    key={act}
                    className="px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px] border border-zinc-700"
                  >
                    {act}
                  </span>
                ))}
              </div>
            </div>
          )}

          {affectedDocuments.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-500 font-mono text-[11px]">Required Documents:</span>
              <div className="flex flex-wrap gap-1">
                {affectedDocuments.map((doc) => (
                  <span
                    key={doc}
                    className="px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px] border border-zinc-700"
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
