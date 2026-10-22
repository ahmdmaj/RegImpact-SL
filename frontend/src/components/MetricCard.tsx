"use client";

import React from "react";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  icon?: LucideIcon;
  variant?: "neutral" | "success" | "warning" | "danger" | "info";
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  icon: Icon,
  variant = "neutral",
}) => {
  const variantDots = {
    neutral: "bg-zinc-500",
    success: "bg-emerald-400",
    warning: "bg-amber-400",
    danger: "bg-rose-400",
    info: "bg-zinc-400",
  };

  return (
    <div className="p-3.5 rounded-lg border border-zinc-800 bg-zinc-900 flex flex-col justify-between">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${variantDots[variant]}`} />
          <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">
            {label}
          </span>
        </div>
        {Icon && (
          <div className="text-zinc-500">
            <Icon className="w-3.5 h-3.5" />
          </div>
        )}
      </div>

      <div className="mt-2.5 flex items-baseline gap-1.5">
        <span className="text-xl font-semibold tracking-tight text-zinc-100">
          {value}
        </span>
        {subtext && (
          <span className="text-[11px] font-mono text-zinc-500">
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
};
