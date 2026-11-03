"use client";

import React from "react";
import { Sparkles, ArrowRight, Store, Factory, HelpCircle, ShieldAlert } from "lucide-react";

export type PresetScenarioType = "retail" | "b2b" | "incomplete" | "exempt";

interface ScenarioPresetCardsProps {
  onSelectPreset: (type: PresetScenarioType) => void;
  activePreset?: PresetScenarioType | null;
}

export const ScenarioPresetCards: React.FC<ScenarioPresetCardsProps> = ({
  onSelectPreset,
  activePreset,
}) => {
  const presets = [
    {
      id: "retail" as const,
      title: "Retail Packaged Food",
      desc: "Prepackaged fruit jam/biscuits. Triggers Regulation 3 universal retail mandate.",
      tag: "Mandatory Retail",
      dot: "bg-emerald-400",
      icon: Store,
    },
    {
      id: "b2b" as const,
      title: "B2B Bulk Processor",
      desc: "Industrial bulk fruit pulp in drums. Triggers 10 B2B disclosures + 3mm label mark.",
      tag: "Mandatory B2B",
      dot: "bg-sky-400",
      icon: Factory,
    },
    {
      id: "incomplete" as const,
      title: "Incomplete Channel",
      desc: "Channel field missing. Triggers 3-valued Kleene clarifying questions.",
      tag: "Missing Data",
      dot: "bg-amber-400",
      icon: HelpCircle,
    },
    {
      id: "exempt" as const,
      title: "Over-the-Counter",
      desc: "Packaged in presence of purchaser. Triggers statutory exception (Proviso a).",
      tag: "Statutory Exemption",
      dot: "bg-zinc-400",
      icon: ShieldAlert,
    },
  ];

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-zinc-400" />
          <span>Benchmark Demonstration Presets</span>
        </label>
        <span className="text-[10px] text-zinc-500 font-mono">Instant UAT Test Cases</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {presets.map((p) => {
          const isActive = activePreset === p.id;
          const Icon = p.icon;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelectPreset(p.id)}
              className={`p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-2.5 ${
                isActive
                  ? "bg-zinc-850/90 border-zinc-600 shadow-md ring-1 ring-zinc-500/30"
                  : "bg-zinc-900/60 border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-850/40"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-zinc-400 bg-zinc-950/70 px-1.5 py-0.5 rounded border border-zinc-800">
                    <span className={`w-1.5 h-1.5 rounded-full ${p.dot}`} />
                    <span>{p.tag}</span>
                  </span>
                  <Icon className="w-3.5 h-3.5 text-zinc-500" />
                </div>
                <h4 className="text-xs font-semibold text-zinc-100">
                  {p.title}
                </h4>
                <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">
                  {p.desc}
                </p>
              </div>

              <div className="text-[10px] font-medium flex items-center justify-between pt-2 border-t border-zinc-800/70 mt-0.5">
                <span className={isActive ? "text-zinc-200 font-semibold" : "text-zinc-500"}>
                  {isActive ? "Active Preset" : "Apply Preset"}
                </span>
                <ArrowRight className={`w-3 h-3 ${isActive ? "text-zinc-200" : "text-zinc-600"}`} />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
