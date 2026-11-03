"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { RoleSwitcher } from "./RoleSwitcher";
import { getHealth, getPendingReviews, UserRole, getCurrentUserRole } from "@/services/api";
import { 
  FileCheck2, 
  Scale, 
  BarChart3, 
  Menu,
  X,
  Shield,
  Layers
} from "lucide-react";

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [role, setRole] = useState<UserRole>("admin");
  const [engineConnected, setEngineConnected] = useState<boolean | null>(null);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  useEffect(() => {
    let isMounted = true;
    const fetchStatus = async () => {
      try {
        await getHealth();
        if (isMounted) setEngineConnected(true);
      } catch {
        if (isMounted) setEngineConnected(false);
      }

      if (role === "reviewer" || role === "admin") {
        try {
          const queue = await getPendingReviews();
          if (isMounted) setPendingCount(queue.length);
        } catch {
          if (isMounted) setPendingCount(0);
        }
      } else {
        if (isMounted) setPendingCount(0);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [role]);

  const navLinks = [
    {
      name: "Compliance Assessor",
      href: "/",
      icon: FileCheck2,
      active: pathname === "/",
      visible: true,
      description: "SME business profile & impact evaluation",
    },
    {
      name: "Reviewer Portal",
      href: "/admin/reviews",
      icon: Scale,
      active: pathname.startsWith("/admin"),
      badge: pendingCount > 0 ? pendingCount : undefined,
      visible: role === "reviewer" || role === "admin",
      description: "Human-in-the-loop candidate adjudication",
    },
    {
      name: "Evaluation Dashboard",
      href: "/evaluation",
      icon: BarChart3,
      active: pathname.startsWith("/evaluation"),
      visible: role === "admin",
      description: "Empirical benchmark metrics & ablations",
    },
  ].filter((item) => item.visible);

  return (
    <nav className="sticky top-0 z-50 bg-zinc-950/90 backdrop-blur-md border-b border-zinc-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-15">
          {/* Brand & Badge */}
          <div className="flex items-center gap-7">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-100 font-bold text-sm shadow-sm group-hover:border-zinc-700 transition-colors">
                <span className="bg-gradient-to-br from-zinc-100 to-zinc-400 bg-clip-text text-transparent">R</span>
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-zinc-100 tracking-tight font-sans">
                    RegImpact-SL
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                    v1.0
                  </span>
                </div>
                <span className="text-[10px] text-zinc-500 font-medium tracking-tight">
                  Sri Lanka Regulatory Intelligence
                </span>
              </div>
            </Link>

            {/* Desktop Navigation Links */}
            <div className="hidden md:flex items-center gap-1.5">
              {navLinks.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      item.active
                        ? "bg-zinc-900 text-zinc-100 border border-zinc-700/80 shadow-sm"
                        : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/60"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{item.name}</span>
                    {item.badge !== undefined && (
                      <span className="ml-1 px-1.5 py-0.2 text-[10px] font-mono rounded bg-amber-950/80 text-amber-300 border border-amber-800/60">
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
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs border border-zinc-800/80 bg-zinc-900/80 text-zinc-300 shadow-sm">
              {engineConnected === true ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="font-mono text-[11px] text-zinc-400">Engine Online</span>
                </>
              ) : engineConnected === false ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span className="font-mono text-[11px] text-rose-400">Engine Offline</span>
                </>
              ) : (
                <span className="font-mono text-[11px] text-zinc-500">Connecting...</span>
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
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 bg-zinc-900 border border-zinc-800"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-zinc-800 bg-zinc-950 px-4 pt-2.5 pb-4 space-y-1.5">
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium ${
                  item.active
                    ? "bg-zinc-900 text-zinc-100 border border-zinc-700"
                    : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/50"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4 text-zinc-400" />
                  <span>{item.name}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-1.5 py-0.2 text-[10px] font-mono rounded bg-amber-950 text-amber-300 border border-amber-800">
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
