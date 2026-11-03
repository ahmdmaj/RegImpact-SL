"use client";

import React, { useEffect, useState } from "react";
import { UserRole, getCurrentUserRole, setCurrentUserRole } from "@/services/api";
import { Shield, Scale, Building2, ChevronDown, Check } from "lucide-react";

interface RoleOption {
  role: UserRole;
  label: string;
  badge: string;
  desc: string;
}

const ROLES: RoleOption[] = [
  {
    role: "sme_user",
    label: "SME User",
    badge: "Food Business",
    desc: "Self-assessment, profile evaluation & operational checklist",
  },
  {
    role: "reviewer",
    label: "Legal Reviewer",
    badge: "Adjudication",
    desc: "Inspect candidate rules and submit audit rationales",
  },
  {
    role: "admin",
    label: "Administrator",
    badge: "Full System",
    desc: "Corpus management, document upload & empirical benchmarks",
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
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-850 text-xs text-zinc-300 border border-zinc-800 transition-colors cursor-pointer shadow-sm"
        title="Switch simulated RBAC user role"
      >
        <span className="text-[10px] uppercase font-mono text-zinc-500 font-medium">Role:</span>
        <div className="flex items-center gap-1.5">
          {role === "admin" && <Shield className="w-3.5 h-3.5 text-zinc-300" />}
          {role === "reviewer" && <Scale className="w-3.5 h-3.5 text-amber-400" />}
          {role === "sme_user" && <Building2 className="w-3.5 h-3.5 text-emerald-400" />}
          <span className="font-medium text-zinc-100">{currentOption.label}</span>
        </div>
        <ChevronDown className={`w-3.5 h-3.5 text-zinc-500 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 w-76 rounded-xl bg-zinc-900 border border-zinc-800 shadow-2xl p-1.5 z-50 space-y-1">
            <div className="px-3 py-2 border-b border-zinc-800/80 text-[10px] font-mono text-zinc-400 uppercase tracking-wider flex items-center justify-between">
              <span>Simulated Persona (RBAC)</span>
              <span className="text-zinc-600 font-sans">Prototype</span>
            </div>
            {ROLES.map((r) => {
              const active = r.role === role;
              return (
                <button
                  key={r.role}
                  type="button"
                  onClick={() => handleSelectRole(r.role)}
                  className={`w-full text-left p-2.5 rounded-lg transition-colors cursor-pointer flex items-start justify-between gap-2.5 ${
                    active ? "bg-zinc-800 text-white border border-zinc-700/80" : "hover:bg-zinc-800/40 text-zinc-300"
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-zinc-100">{r.label}</span>
                      <span className="px-1.5 py-0.2 text-[9px] font-mono rounded bg-zinc-950 text-zinc-400 border border-zinc-800">
                        {r.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-snug">{r.desc}</p>
                  </div>
                  {active && <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
