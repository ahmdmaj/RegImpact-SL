"use client";

import React from "react";
import { Sparkles, Building2, HelpCircle, ShieldCheck } from "lucide-react";

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
      title: "Large Industrial Manufacturer",
      subtitle: "Mandatory Thresholds Triggered",
      desc: "25 employees (>20 EPL), 100 kg/day (>50 kg/day FCAU), prepackaged biscuits.",
      badge: "Mandatory Rules",
      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      activeBorder: "border-emerald-500/50 bg-emerald-950/20",
    },
    {
      id: "incomplete" as const,
      title: "Incomplete Bakery Data",
      subtitle: "Kleene Abstention & Clarifications",
      desc: "15 employees, capacity left blank (UNKNOWN). Demonstrates missing data questions.",
      badge: "Questions Demo",
      badgeColor: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      activeBorder: "border-amber-500/50 bg-amber-950/20",
    },
    {
      id: "exempt" as const,
      title: "Micro Cottage Producer",
      subtitle: "Exemption Boundaries",
      desc: "8 employees (<20), 30 kg/day (<50), non-packaged traditional confectioneries.",
      badge: "Exemptions Demo",
      badgeColor: "bg-slate-800 text-slate-300 border-slate-700",
      activeBorder: "border-slate-500 bg-slate-800/40",
    },
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-slate-400" />
          <span>Interactive Benchmark Scenarios</span>
        </label>
        <span className="text-[11px] text-slate-500 font-mono">1-Click Quick Configuration</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
        {presets.map((p) => {
          const isActive = activePreset === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelectPreset(p.id)}
              className={`p-3 rounded-lg border text-left transition-all cursor-pointer flex flex-col justify-between gap-2 ${
                isActive
                  ? p.activeBorder
                  : "bg-slate-900 border-slate-800 hover:border-slate-700 hover:bg-slate-850"
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${p.badgeColor}`}>
                    {p.badge}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-slate-100">
                  {p.title}
                </h4>
                <p className="text-[11px] text-slate-400 mt-1 leading-snug line-clamp-2">
                  {p.desc}
                </p>
              </div>

              <div className="pt-1 text-[11px] font-medium text-slate-300 flex items-center justify-between border-t border-slate-800/60 mt-1">
                <span>Load Scenario</span>
                <span className="text-slate-500">&rarr;</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
