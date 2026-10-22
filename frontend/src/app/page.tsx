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
import { Navbar } from "@/components/Navbar";
import { ProfileForm } from "@/components/ProfileForm";
import { ClarifyingQuestionsPanel } from "@/components/ClarifyingQuestionsPanel";
import { ImpactReportView } from "@/components/ImpactReportView";
import { EvidenceViewer } from "@/components/EvidenceViewer";
import {
  ListChecks,
  HelpCircle,
  ShieldCheck,
  AlertCircle,
  FileCheck2,
  BookOpen,
  ArrowRight,
  Sparkles,
  Scale
} from "lucide-react";

export default function Home() {
  const [healthStatus, setHealthStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [regulations, setRegulations] = useState<ClauseVersion[]>([]);
  
  const [currentProfile, setCurrentProfile] = useState<BusinessProfile | null>(null);
  const [currentAsAtDate, setCurrentAsAtDate] = useState<string>("2024-08-01");
  const [report, setReport] = useState<StructuredImpactReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeResultTab, setActiveResultTab] = useState<"overview" | "questions" | "evidence">("overview");

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
      setActiveResultTab("overview");
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
    handleAnalyze(updated, currentAsAtDate);
  };

  return (
    <div className="min-h-screen text-slate-100 flex flex-col bg-[#0b0f19]">
      {/* 1. Global Enterprise Navigation Bar */}
      <Navbar />

      {/* 2. Main Content Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Backend Offline Warning */}
        {healthStatus === "disconnected" && (
          <div className="mb-6 p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>
                Backend API offline (<code className="font-mono">http://localhost:8000</code>). Ensure FastAPI service is running.
              </span>
            </div>
            <button
              onClick={checkBackendHealth}
              className="px-2.5 py-1 rounded bg-rose-900/50 hover:bg-rose-800 text-white font-medium text-xs transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Global Error Banner */}
        {errorMessage && (
          <div className="mb-6 p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-400 hover:text-white font-bold text-sm px-1"
            >
              &times;
            </button>
          </div>
        )}

        {/* Workspace 2-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: SME Profile Configurator */}
          <div className="lg:col-span-5 space-y-6">
            <ProfileForm
              onAnalyze={handleAnalyze}
              isLoading={isLoading}
              initialAsAtDate={currentAsAtDate}
            />

            {/* Standard Statutory Regulations In-Corpus Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 shadow-sm p-5 space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300 pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-slate-400" />
                  <span>Statutory Regulatory Corpus</span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  {regulations.length > 0 ? `${regulations.length} Indexed Clauses` : "Authoritative Corpus"}
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="flex items-center justify-between font-medium text-slate-200">
                    <span>FCAU Regulation 4 (Labelling & Packaging)</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">Gazette 2024/01</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Threshold: Capacity &ge; 50 kg/day, Prepackaged food. Requires trilingual nutritional panel declarations.
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="flex items-center justify-between font-medium text-slate-200">
                    <span>CEA EPL Schedule 1 Part B Item 12</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">Gazette 1533/16</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Threshold: Workforce &ge; 20 persons in food manufacturing. Requires Environmental Protection Licence.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Output Results */}
          <div className="lg:col-span-7 space-y-6">
            {report ? (
              <div className="space-y-5">
                {/* Result Tabs Navigation */}
                <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-800">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <button
                      type="button"
                      onClick={() => setActiveResultTab("overview")}
                      className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                        activeResultTab === "overview"
                          ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                          : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                      }`}
                    >
                      <ListChecks className="w-4 h-4" />
                      <span>Action Plan & Summary</span>
                    </button>

                    {report.clarifying_questions && report.clarifying_questions.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setActiveResultTab("questions")}
                        className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                          activeResultTab === "questions"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm"
                            : "text-amber-400/80 hover:text-amber-300 hover:bg-amber-500/10"
                        }`}
                      >
                        <HelpCircle className="w-4 h-4" />
                        <span>Clarifications ({report.clarifying_questions.length})</span>
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => setActiveResultTab("evidence")}
                      className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                        activeResultTab === "evidence"
                          ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                          : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                      }`}
                    >
                      <ShieldCheck className="w-4 h-4" />
                      <span>Legal Citations ({report.evaluations.length})</span>
                    </button>
                  </div>

                  <span className="text-[11px] text-slate-500 font-mono hidden sm:inline-block">
                    As-At: {currentAsAtDate}
                  </span>
                </div>

                {/* Tab 1: Overview & Actions */}
                {activeResultTab === "overview" && (
                  <ImpactReportView report={report} />
                )}

                {/* Tab 2: Clarifying Questions */}
                {activeResultTab === "questions" && (
                  <ClarifyingQuestionsPanel
                    questions={report.clarifying_questions}
                    missingFields={report.missing_fields}
                    onAnswerField={handleAnswerMissingField}
                    onReevaluate={() => {
                      if (currentProfile) handleAnalyze(currentProfile, currentAsAtDate);
                    }}
                  />
                )}

                {/* Tab 3: Detailed Statutory Evidence */}
                {activeResultTab === "evidence" && (
                  <EvidenceViewer evaluations={report.evaluations} />
                )}
              </div>
            ) : (
              /* Ready / Empty State */
              <div className="rounded-xl border border-slate-800 bg-slate-900 shadow-sm p-10 text-center space-y-6">
                <div className="w-12 h-12 mx-auto rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                  <FileCheck2 className="w-6 h-6 text-slate-400" />
                </div>

                <div className="max-w-md mx-auto space-y-2">
                  <h3 className="text-sm font-semibold text-white">
                    Compliance Assessor Ready
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Select a benchmark scenario preset on the left or customize your business profile parameters.
                    Click <strong className="text-slate-200">Run Regulatory Compliance Analysis</strong> to execute the neuro-symbolic engine.
                  </p>
                </div>

                {/* System Pillars */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-left">
                  <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block font-semibold">
                      3-Valued Kleene Logic
                    </span>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      Rigorous separation of exemptions from missing data. Eliminates hallucination.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block font-semibold">
                      Statutory Grounding
                    </span>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      Verbatim citations traceable to exact Gazette page numbers and character offsets.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block font-semibold">
                      Sensitivity Bounds
                    </span>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      Automated boundary reasoning for worker headcount and production capacities.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* 3. Global Minimal Footer */}
      <footer className="mt-auto border-t border-slate-800 bg-[#0d131f] py-4 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">RegImpact-SL</span>
            <span>&bull;</span>
            <span>Sri Lanka Food Regulatory Compliance Platform</span>
          </div>
          <div className="font-mono text-[11px] text-slate-500">
            Neuro-Symbolic Legal Intelligence Engine
          </div>
        </div>
      </footer>
    </div>
  );
}
