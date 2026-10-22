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
    <nav className="sticky top-0 z-50 bg-zinc-950/80 backdrop-blur-md border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Brand & Badge */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-7 h-7 rounded-md bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-100 font-bold text-xs group-hover:border-zinc-700 transition-colors">
                R
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-zinc-100 tracking-tight">
                  RegImpact-SL
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                  v1.0
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
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      item.active
                        ? "bg-zinc-900 text-zinc-100 border border-zinc-800"
                        : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/50"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{item.name}</span>
                    {item.badge !== undefined && (
                      <span className="ml-0.5 px-1.5 py-0.2 text-[10px] font-mono rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Right Status Controls */}
          <div className="hidden sm:flex items-center gap-2.5">
            {/* Engine Status */}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-md text-xs border border-zinc-800 bg-zinc-900 text-zinc-300">
              {engineConnected === true ? (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span className="font-mono text-[11px] text-zinc-400">Engine Online</span>
                </>
              ) : engineConnected === false ? (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  <span className="font-mono text-[11px] text-zinc-400">Engine Offline</span>
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
              className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 bg-zinc-900 border border-zinc-800"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-zinc-800 bg-zinc-950 px-4 pt-2 pb-3 space-y-1">
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium ${
                  item.active
                    ? "bg-zinc-900 text-zinc-100 border border-zinc-800"
                    : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/50"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.name}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-1.5 py-0.2 text-[10px] font-mono rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
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
