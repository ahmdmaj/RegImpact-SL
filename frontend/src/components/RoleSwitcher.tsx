"use client";

import React, { useEffect, useState } from "react";
import { UserRole, getCurrentUserRole, setCurrentUserRole } from "@/services/api";
import { Shield, Scale, Building2, ChevronDown, Check } from "lucide-react";

interface RoleOption {
  role: UserRole;
  label: string;
  badge: string;
  color: string;
  desc: string;
}

const ROLES: RoleOption[] = [
  {
    role: "admin",
    label: "Admin",
    badge: "Full Access",
    color: "text-purple-400 bg-purple-500/10 border-purple-500/30",
    desc: "Ingestion, LLM compilation, legal reviews & engine analysis",
  },
  {
    role: "reviewer",
    label: "Legal Reviewer",
    badge: "Verification",
    color: "text-amber-400 bg-amber-500/10 border-amber-500/30",
    desc: "Adjudicate candidate rules in the review queue",
  },
  {
    role: "sme_user",
    label: "SME User",
    badge: "Food Business",
    color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    desc: "Food manufacturer profile evaluation & action checklist",
  },
];

export const RoleSwitcher: React.FC = () => {
  const [role, setRole] = useState<UserRole>("admin");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setRole(getCurrentUserRole());

    const handleRoleChange = (e: Event) => {
      const customEvent = e as CustomEvent<{ role: UserRole }>;
      if (customEvent.detail?.role) {
        setRole(customEvent.detail.role);
      }
    };

    window.addEventListener("regimpact:role_change", handleRoleChange);
    return () => window.removeEventListener("regimpact:role_change", handleRoleChange);
  }, []);

  const handleSelectRole = (newRole: UserRole) => {
    setCurrentUserRole(newRole);
    setRole(newRole);
    setOpen(false);
  };

  const currentOption = ROLES.find((r) => r.role === role) || ROLES[0];

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs text-slate-200 border border-slate-700/80 transition-all cursor-pointer shadow-sm"
        title="Switch simulated RBAC user role"
      >
        <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">Role:</span>
        <div className="flex items-center gap-1.5">
          {role === "admin" && <Shield className="w-3.5 h-3.5 text-purple-400" />}
          {role === "reviewer" && <Scale className="w-3.5 h-3.5 text-amber-400" />}
          {role === "sme_user" && <Building2 className="w-3.5 h-3.5 text-emerald-400" />}
          <span className="font-medium text-slate-200">{currentOption.label}</span>
        </div>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-slate-900 border border-slate-700/80 shadow-2xl p-2 z-50 space-y-1">
            <div className="px-3 py-2 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Simulated Role-Based Access (RBAC)
            </div>
            {ROLES.map((r) => {
              const active = r.role === role;
              return (
                <button
                  key={r.role}
                  type="button"
                  onClick={() => handleSelectRole(r.role)}
                  className={`w-full text-left p-2.5 rounded-lg transition-colors cursor-pointer flex items-start justify-between gap-2 ${
                    active ? "bg-slate-800 text-white" : "hover:bg-slate-800/60 text-slate-300"
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-100">{r.label}</span>
                      <span className={`px-1.5 py-0.5 text-[9px] font-mono rounded border ${r.color}`}>
                        {r.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-tight">{r.desc}</p>
                  </div>
                  {active && <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-1" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
