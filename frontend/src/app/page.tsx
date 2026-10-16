"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  BusinessProfile,
  ClauseVersion,
  StructuredImpactReport,
  getHealth,
  getRegulations,
  runAnalysis,
} from "@/services/api";
import { ProfileForm } from "@/components/ProfileForm";
import { ClarifyingQuestionsPanel } from "@/components/ClarifyingQuestionsPanel";
import { ImpactReportView } from "@/components/ImpactReportView";
import { EvidenceViewer } from "@/components/EvidenceViewer";
import Link from "next/link";
import {
  Shield,
  Activity,
  Layers,
  BookOpen,
  Sparkles,
  AlertCircle,
  RefreshCw,
  CheckCircle,
  Cpu,
  Info,
  BarChart3,
} from "lucide-react";

export default function Home() {
  const [healthStatus, setHealthStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [regulations, setRegulations] = useState<ClauseVersion[]>([]);
  const [showCatalogModal, setShowCatalogModal] = useState(false);
  
  const [currentProfile, setCurrentProfile] = useState<BusinessProfile | null>(null);
  const [currentAsAtDate, setCurrentAsAtDate] = useState<string>("2024-08-01");
  const [report, setReport] = useState<StructuredImpactReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Check health and load catalog on mount
  const checkBackendHealth = useCallback(async () => {
    setHealthStatus("checking");
    try {
      await getHealth();
      setHealthStatus("connected");
      try {
        const regs = await getRegulations();
        setRegulations(regs);
      } catch {
        // Regulations fetch secondary
      }
    } catch {
      setHealthStatus("disconnected");
    }
  }, []);

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  // Main Analysis Trigger
  const handleAnalyze = async (profile: BusinessProfile, asAtDate: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    setCurrentProfile(profile);
    setCurrentAsAtDate(asAtDate);

    try {
      const res = await runAnalysis({
        business_profile: profile,
        as_at_date: asAtDate,
      });
      setReport(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run regulatory analysis.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // Inline answering of missing fields from ClarifyingQuestionsPanel
  const handleAnswerMissingField = (field: string, value: unknown) => {
    if (!currentProfile) return;

    const updated = { ...currentProfile };

    if (field === "production_capacity.kg_per_day" || field === "production_capacity.value") {
      updated.production_capacity = {
        ...(updated.production_capacity || { unit: "kg", per_period: "day" }),
        value: typeof value === "number" ? value : Number(value),
      };
    } else if (field === "employee_count") {
      updated.employee_count = typeof value === "number" ? value : Number(value);
    } else if (field === "products.prepackaged") {
      if (updated.products && updated.products.length > 0) {
        updated.products[0].prepackaged = Boolean(value);
      } else {
        updated.products = [{ category: "food", prepackaged: Boolean(value) }];
      }
    } else if (field === "activity") {
      updated.activity = String(value);
    }

    setCurrentProfile(updated);
    // Re-trigger analysis automatically with newly supplied field
    handleAnalyze(updated, currentAsAtDate);
  };

  return (
    <div className="min-h-screen text-slate-100 flex flex-col selection:bg-blue-500/30 selection:text-blue-200">
      {/* 1. Header Bar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Platform Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white font-black text-lg">
              R
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-white">
                  RegImpact-SL
                </h1>
                <span className="px-1.5 py-0.5 text-[10px] font-mono font-semibold rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  v1.0 &bull; Sri Lanka
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Neuro-Symbolic Regulatory Intelligence for Food Manufacturers
              </p>
            </div>
          </div>

          {/* Backend Health Status & Catalog Button */}
          <div className="flex items-center gap-3">
            <Link
              href="/evaluation"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-xs text-indigo-300 border border-indigo-500/30 transition-colors"
            >
              <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Evaluation Dashboard</span>
            </Link>

            <button
              type="button"
              onClick={() => setShowCatalogModal(!showCatalogModal)}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700 transition-colors cursor-pointer"
            >
              <BookOpen className="w-3.5 h-3.5 text-blue-400" />
              <span>Statutory Catalog ({regulations.length})</span>
            </button>

            {/* Health Status Pill */}
            <div
              className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${
                healthStatus === "connected"
                  ? "bg-emerald-950/60 text-emerald-300 border-emerald-700/50"
                  : healthStatus === "checking"
                  ? "bg-slate-800 text-slate-400 border-slate-700"
                  : "bg-rose-950/60 text-rose-300 border-rose-700/50"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  healthStatus === "connected"
                    ? "bg-emerald-400 animate-pulse"
                    : healthStatus === "checking"
                    ? "bg-amber-400 animate-ping"
                    : "bg-rose-500"
                }`}
              />
              <span className="capitalize">
                {healthStatus === "connected" ? "Engine Active (Port 8000)" : healthStatus === "checking" ? "Checking Engine..." : "Engine Offline"}
              </span>
              {healthStatus === "disconnected" && (
                <button
                  type="button"
                  onClick={checkBackendHealth}
                  className="hover:text-white transition-colors cursor-pointer"
                  title="Retry connection"
                >
                  <RefreshCw className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* 2. Main Workspace Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Offline Warning Notice if Backend is not running */}
        {healthStatus === "disconnected" && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
              <div>
                <span className="font-semibold">FastAPI Engine Offline:</span> Cannot connect to{" "}
                <code className="bg-rose-900/40 px-1 py-0.5 rounded font-mono">http://localhost:8000</code>.
                Make sure the backend is running with{" "}
                <code className="bg-rose-900/40 px-1 py-0.5 rounded font-mono">uvicorn backend.src.main:app --reload</code>.
              </div>
            </div>
            <button
              onClick={checkBackendHealth}
              className="px-3 py-1 rounded bg-rose-800 hover:bg-rose-700 text-white font-medium text-xs cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Global Error Banner */}
        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-400 hover:text-white font-bold text-sm"
            >
              &times;
            </button>
          </div>
        )}

        {/* Main Grid: Form on Left, Output & Evidence on Right */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: SME Profile Configurator */}
          <div className="lg:col-span-5 space-y-6">
            <ProfileForm
              onAnalyze={handleAnalyze}
              isLoading={isLoading}
              initialAsAtDate={currentAsAtDate}
            />

            {/* In-Memory Statutory Rules Catalog Card */}
            <div className="glass-panel rounded-2xl p-5 border border-slate-700/60 shadow-lg space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300 pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-blue-400" />
                  <span>Configured Statutory Regulations</span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  {regulations.length > 0 ? `${regulations.length} Clauses` : "2 Standard Seed Clauses"}
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between font-medium text-slate-200">
                    <span>FCAU Regulation 4 (Labelling & Packaging)</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">Gazette 2024/01</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Threshold: Capacity &ge; 50 kg/day, Prepackaged food. Requires trilingual nutritional panel.
                  </p>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between font-medium text-slate-200">
                    <span>CEA EPL Schedule 1 Part B Item 12</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">Gazette 1533/16</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Threshold: Employees &ge; 20 persons in food manufacturing. Requires Environmental Protection Licence.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Dynamic Analysis Dashboard, Clarifying Questions, and Evidence */}
          <div className="lg:col-span-7 space-y-6">
            {report ? (
              <>
                {/* 1. Clarifying Questions (rendered when CONDITIONAL_MISSING_DATA occurs) */}
                {report.clarifying_questions && report.clarifying_questions.length > 0 && (
                  <ClarifyingQuestionsPanel
                    questions={report.clarifying_questions}
                    missingFields={report.missing_fields}
                    onAnswerField={handleAnswerMissingField}
                    onReevaluate={() => {
                      if (currentProfile) handleAnalyze(currentProfile, currentAsAtDate);
                    }}
                  />
                )}

                {/* 2. Structured Impact Report View */}
                <ImpactReportView report={report} />

                {/* 3. Statutory Evidence & Trace Audit Viewer */}
                <EvidenceViewer evaluations={report.evaluations} />
              </>
            ) : (
              /* Empty / Welcome State */
              <div className="glass-panel rounded-2xl p-10 border border-slate-700/60 shadow-xl text-center space-y-6">
                <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-tr from-blue-500/20 to-indigo-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shadow-inner">
                  <Cpu className="w-8 h-8 text-blue-400" />
                </div>

                <div className="max-w-md mx-auto space-y-2">
                  <h3 className="text-lg font-bold text-white">
                    Deterministic Regulatory Impact Engine Ready
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Select one of the scenario presets on the left or customize your business profile parameters.
                    Click <strong className="text-blue-400 font-semibold">Analyze Regulatory Impact</strong> to run the full neuro-symbolic pipeline.
                  </p>
                </div>

                {/* Key Architecture Features */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 text-left">
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                    <span className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider block">
                      3-Valued Kleene Logic
                    </span>
                    <p className="text-xs text-slate-400 mt-1">
                      Distinguishes true exemptions from missing data. Refuses to guess or hallucinate.
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                    <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block">
                      Evidence Grounded
                    </span>
                    <p className="text-xs text-slate-400 mt-1">
                      Every statement in executive summaries is audited against exact gazette quote spans.
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                    <span className="text-[11px] font-semibold text-purple-400 uppercase tracking-wider block">
                      Counterfactual Reasoning
                    </span>
                    <p className="text-xs text-slate-400 mt-1">
                      Calculates minimal capacity or staffing changes that flip compliance obligations.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* 3. Footer */}
      <footer className="mt-auto border-t border-slate-800 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">RegImpact-SL</span>
            <span>&bull;</span>
            <span>Section 8.7 Reference Implementation</span>
          </div>
          <div>
            Built with Next.js 16, TypeScript, Tailwind CSS, & FastAPI
          </div>
        </div>
      </footer>
    </div>
  );
}
