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
    role: "admin",
    label: "Admin",
    badge: "Full Access",
    desc: "Ingestion, LLM compilation, legal reviews & engine analysis",
  },
  {
    role: "reviewer",
    label: "Legal Reviewer",
    badge: "Verification",
    desc: "Adjudicate candidate rules in the review queue",
  },
  {
    role: "sme_user",
    label: "SME User",
    badge: "Food Business",
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
        className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-900 hover:bg-zinc-850 text-xs text-zinc-300 border border-zinc-800 transition-colors cursor-pointer"
        title="Switch simulated RBAC user role"
      >
        <span className="text-[10px] uppercase font-mono text-zinc-500">Role:</span>
        <div className="flex items-center gap-1.5">
          {role === "admin" && <Shield className="w-3.5 h-3.5 text-zinc-300" />}
          {role === "reviewer" && <Scale className="w-3.5 h-3.5 text-zinc-300" />}
          {role === "sme_user" && <Building2 className="w-3.5 h-3.5 text-zinc-300" />}
          <span className="font-medium text-zinc-200">{currentOption.label}</span>
        </div>
        <ChevronDown className="w-3 h-3 text-zinc-500" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1.5 w-72 rounded-lg bg-zinc-900 border border-zinc-800 shadow-xl p-1.5 z-50 space-y-1">
            <div className="px-2.5 py-1.5 border-b border-zinc-800 text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
              Simulated Role-Based Access (RBAC)
            </div>
            {ROLES.map((r) => {
              const active = r.role === role;
              return (
                <button
                  key={r.role}
                  type="button"
                  onClick={() => handleSelectRole(r.role)}
                  className={`w-full text-left p-2 rounded-md transition-colors cursor-pointer flex items-start justify-between gap-2 ${
                    active ? "bg-zinc-800 text-white" : "hover:bg-zinc-800/50 text-zinc-300"
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-zinc-100">{r.label}</span>
                      <span className="px-1.5 py-0.2 text-[9px] font-mono rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                        {r.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-tight">{r.desc}</p>
                  </div>
                  {active && <Check className="w-3.5 h-3.5 text-zinc-200 shrink-0 mt-1" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
