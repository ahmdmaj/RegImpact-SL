"use client";

import React from "react";
import { Sparkles } from "lucide-react";

interface ScenarioPresetCardsProps {
  onSelectPreset: (type: "compliant" | "incomplete" | "exempt") => void;
  activePreset?: "compliant" | "incomplete" | "exempt" | null;
}

export const ScenarioPresetCards: React.FC<ScenarioPresetCardsProps> = ({
  onSelectPreset,
  activePreset,
}) => {
  const presets = [
    {
      id: "compliant" as const,
      title: "Large Manufacturer",
      desc: "25 employees, 100 kg/day capacity, prepackaged biscuits.",
      tag: "Mandatory Rules",
      dot: "bg-emerald-400",
    },
    {
      id: "incomplete" as const,
      title: "Incomplete Bakery",
      desc: "15 employees, capacity unknown. Tests Kleene clarifications.",
      tag: "Missing Data",
      dot: "bg-amber-400",
    },
    {
      id: "exempt" as const,
      title: "Micro Cottage",
      desc: "8 employees, 30 kg/day capacity, bulk unpackaged sweets.",
      tag: "Exemptions",
      dot: "bg-zinc-400",
    },
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-zinc-500" />
          <span>Scenario Presets</span>
        </label>
        <span className="text-[11px] text-zinc-500 font-mono">1-Click Test Scenarios</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {presets.map((p) => {
          const isActive = activePreset === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelectPreset(p.id)}
              className={`p-2.5 rounded-lg border text-left transition-colors cursor-pointer flex flex-col justify-between gap-1.5 ${
                isActive
                  ? "bg-zinc-800/80 border-zinc-600 text-zinc-100"
                  : "bg-zinc-900/60 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/40 text-zinc-300"
              }`}
            >
              <div>
                <div className="flex items-center gap-1.5 mb-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${p.dot}`} />
                  <span className="text-[10px] font-mono text-zinc-400">{p.tag}</span>
                </div>
                <h4 className="text-xs font-medium text-zinc-200">
                  {p.title}
                </h4>
                <p className="text-[11px] text-zinc-500 mt-0.5 leading-snug">
                  {p.desc}
                </p>
              </div>

              <div className="text-[10px] text-zinc-500 flex items-center justify-between pt-1 border-t border-zinc-800/60 mt-0.5">
                <span>{isActive ? "Active Preset" : "Apply"}</span>
                <span>&rarr;</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
