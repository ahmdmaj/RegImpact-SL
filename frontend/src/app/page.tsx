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
    <div className="min-h-screen text-zinc-100 flex flex-col bg-zinc-950 font-sans">
      {/* 1. Global Enterprise Navigation Bar */}
      <Navbar />

      {/* 2. Main Content Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Backend Offline Warning */}
        {healthStatus === "disconnected" && (
          <div className="mb-4 p-3 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              <span>
                Backend API offline (<code className="font-mono text-zinc-400">http://localhost:8000</code>). Ensure FastAPI service is running.
              </span>
            </div>
            <button
              onClick={checkBackendHealth}
              className="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Global Error Banner */}
        {errorMessage && (
          <div className="mb-4 p-3 rounded-md bg-zinc-900 border border-rose-900/50 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-zinc-400 hover:text-white font-bold text-sm px-1"
            >
              &times;
            </button>
          </div>
        )}

        {/* Workspace 2-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: SME Profile Configurator */}
          <div className="lg:col-span-5 space-y-4">
            <ProfileForm
              onAnalyze={handleAnalyze}
              isLoading={isLoading}
              initialAsAtDate={currentAsAtDate}
            />

            {/* Statutory Regulations In-Corpus Card */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-medium text-zinc-300 pb-2 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Statutory Regulatory Corpus</span>
                </div>
                <span className="text-[10px] font-mono text-zinc-500">
                  {regulations.length > 0 ? `${regulations.length} Indexed Clauses` : "Official Gazettes"}
                </span>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="p-2.5 rounded-md bg-zinc-950 border border-zinc-850">
                  <div className="flex items-center justify-between font-medium text-zinc-200">
                    <span className="text-[11px]">FCAU Regulation 4 (Labelling & Packaging)</span>
                    <span className="text-[10px] font-mono text-zinc-500">Gazette 2024/01</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Capacity &ge; 50 kg/day, Prepackaged food. Requires trilingual nutritional panel declarations.
                  </p>
                </div>

                <div className="p-2.5 rounded-md bg-zinc-950 border border-zinc-850">
                  <div className="flex items-center justify-between font-medium text-zinc-200">
                    <span className="text-[11px]">CEA EPL Schedule 1 Part B Item 12</span>
                    <span className="text-[10px] font-mono text-zinc-500">Gazette 1533/16</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Workforce &ge; 20 persons in food manufacturing. Requires Environmental Protection Licence.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Output Results */}
          <div className="lg:col-span-7 space-y-4">
            {report ? (
              <div className="space-y-4">
                {/* Result Tabs Navigation */}
                <div className="flex items-center justify-between flex-wrap gap-2 pb-1.5 border-b border-zinc-800">
                  <div className="flex items-center gap-1 flex-wrap">
                    <button
                      type="button"
                      onClick={() => setActiveResultTab("overview")}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                        activeResultTab === "overview"
                          ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
                          : "text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      <ListChecks className="w-3.5 h-3.5" />
                      <span>Action Plan</span>
                    </button>

                    {report.clarifying_questions && report.clarifying_questions.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setActiveResultTab("questions")}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                          activeResultTab === "questions"
                            ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
                            : "text-zinc-400 hover:text-zinc-200"
                        }`}
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                        <span>Clarifications ({report.clarifying_questions.length})</span>
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => setActiveResultTab("evidence")}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                        activeResultTab === "evidence"
                          ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
                          : "text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Citations ({report.evaluations.length})</span>
                    </button>
                  </div>

                  <span className="text-[11px] text-zinc-500 font-mono hidden sm:inline-block">
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
              <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-8 text-center space-y-5">
                <div className="w-10 h-10 mx-auto rounded-md bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300">
                  <FileCheck2 className="w-5 h-5 text-zinc-400" />
                </div>

                <div className="max-w-md mx-auto space-y-1.5">
                  <h3 className="text-xs font-semibold text-zinc-200">
                    Compliance Assessor Ready
                  </h3>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    Select a benchmark scenario on the left or customize your business profile parameters.
                    Click <strong className="text-zinc-200">Analyze Regulatory Impact</strong> to execute the engine.
                  </p>
                </div>

                {/* System Pillars */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1 text-left">
                  <div className="p-3 rounded-md bg-zinc-950 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 block font-medium">
                      Kleene Logic
                    </span>
                    <p className="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">
                      Separates exemptions from missing data. Eliminates hallucination.
                    </p>
                  </div>

                  <div className="p-3 rounded-md bg-zinc-950 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 block font-medium">
                      Statutory Grounding
                    </span>
                    <p className="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">
                      Verbatim citations traceable to exact Gazette page numbers and offsets.
                    </p>
                  </div>

                  <div className="p-3 rounded-md bg-zinc-950 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 block font-medium">
                      Sensitivity Bounds
                    </span>
                    <p className="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">
                      Boundary reasoning for workforce headcount and capacities.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* 3. Global Minimal Footer */}
      <footer className="mt-auto border-t border-zinc-800 bg-zinc-950 py-4 text-xs text-zinc-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-medium text-zinc-400">RegImpact-SL</span>
            <span>&bull;</span>
            <span>Sri Lanka Food Regulatory Compliance Platform</span>
          </div>
          <div className="font-mono text-[11px] text-zinc-600">
            Neuro-Symbolic Legal Intelligence Engine
          </div>
        </div>
      </footer>
    </div>
  );
}
