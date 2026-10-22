"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { RoleSwitcher } from "./RoleSwitcher";
import { getHealth, getPendingReviews } from "@/services/api";
import { 
  FileCheck2, 
  Scale, 
  BarChart3, 
  Activity, 
  CheckCircle2, 
  AlertCircle,
  Menu,
  X,
} from "lucide-react";

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [engineConnected, setEngineConnected] = useState<boolean | null>(null);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchStatus = async () => {
      try {
        await getHealth();
        if (isMounted) setEngineConnected(true);
      } catch {
        if (isMounted) setEngineConnected(false);
      }

      try {
        const queue = await getPendingReviews();
        if (isMounted) setPendingCount(queue.length);
      } catch {
        // Pending reviews fetch secondary
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navLinks = [
    {
      name: "Compliance Assessor",
      href: "/",
      icon: FileCheck2,
      active: pathname === "/",
    },
    {
      name: "Reviewer Portal",
      href: "/admin/reviews",
      icon: Scale,
      active: pathname.startsWith("/admin"),
      badge: pendingCount > 0 ? pendingCount : undefined,
    },
    {
      name: "Evaluation Dashboard",
      href: "/evaluation",
      icon: BarChart3,
      active: pathname.startsWith("/evaluation"),
    },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-[#0d131f]/95 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Badge */}
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-100 font-bold text-sm group-hover:border-slate-500 transition-colors">
                R
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white tracking-tight">
                    RegImpact-SL
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    SL-Corpus
                  </span>
                </div>
                <span className="text-[11px] text-slate-400 hidden sm:block">
                  Neuro-Symbolic Legal Intelligence
                </span>
              </div>
            </Link>

            {/* Desktop Navigation Links */}
            <div className="hidden md:flex items-center gap-1">
              {navLinks.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
                      item.active
                        ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                    {item.badge !== undefined && (
                      <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Right Status Controls */}
          <div className="hidden sm:flex items-center gap-3">
            {/* Engine Status */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs border ${
                engineConnected === true
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : engineConnected === false
                  ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                  : "bg-slate-800 text-slate-400 border-slate-700"
              }`}
            >
              {engineConnected === true ? (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-mono text-[11px]">Engine Active</span>
                </>
              ) : engineConnected === false ? (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span className="font-mono text-[11px]">Engine Offline</span>
                </>
              ) : (
                <span className="font-mono text-[11px]">Connecting...</span>
              )}
            </div>

            {/* RBAC Role Switcher */}
            <RoleSwitcher />
          </div>

          {/* Mobile menu trigger */}
          <div className="flex md:hidden items-center gap-2">
            <RoleSwitcher />
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-400 hover:text-white bg-slate-800 border border-slate-700"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-[#0d131f] px-4 pt-2 pb-4 space-y-1">
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium ${
                  item.active
                    ? "bg-slate-800 text-white border border-slate-700"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
};
