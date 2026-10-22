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
  const variantStyles = {
    neutral: {
      card: "bg-slate-900 border-slate-800 text-slate-100",
      label: "text-slate-400",
      value: "text-slate-100",
      subtext: "text-slate-500",
      iconBg: "bg-slate-800 text-slate-300 border-slate-700",
    },
    success: {
      card: "bg-slate-900 border-emerald-900/40 text-emerald-300",
      label: "text-emerald-400",
      value: "text-emerald-200",
      subtext: "text-emerald-500/80",
      iconBg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    },
    warning: {
      card: "bg-slate-900 border-amber-900/40 text-amber-300",
      label: "text-amber-400",
      value: "text-amber-200",
      subtext: "text-amber-500/80",
      iconBg: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    },
    danger: {
      card: "bg-slate-900 border-rose-900/40 text-rose-300",
      label: "text-rose-400",
      value: "text-rose-200",
      subtext: "text-rose-500/80",
      iconBg: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    },
    info: {
      card: "bg-slate-900 border-sky-900/40 text-sky-300",
      label: "text-sky-400",
      value: "text-sky-200",
      subtext: "text-sky-500/80",
      iconBg: "bg-sky-500/10 text-sky-400 border-sky-500/20",
    },
  };

  const style = variantStyles[variant];

  return (
    <div className={`p-4 rounded-xl border ${style.card} shadow-sm flex flex-col justify-between transition-all`}>
      <div className="flex items-center justify-between gap-2">
        <span className={`text-xs font-medium uppercase tracking-wider ${style.label}`}>
          {label}
        </span>
        {Icon && (
          <div className={`p-1.5 rounded-lg border ${style.iconBg}`}>
            <Icon className="w-3.5 h-3.5" />
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className={`text-2xl font-bold tracking-tight ${style.value}`}>
          {value}
        </span>
        {subtext && (
          <span className={`text-xs font-mono ${style.subtext}`}>
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
};
