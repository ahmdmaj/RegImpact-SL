"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  ReviewItem,
  getPendingReviews,
  approveReview,
  rejectReview,
  uploadDocument,
} from "@/services/api";
import {
  ShieldCheck,
  FileCheck,
  CheckCircle2,
  XCircle,
  Clock,
  UploadCloud,
  FileText,
  AlertTriangle,
  RefreshCw,
  ArrowLeft,
  Scale,
  Sparkles,
  BookOpen,
  Code2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Check,
  AlertCircle,
} from "lucide-react";

export default function AdminReviewsPage() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [reviewerId, setReviewerId] = useState("legal_officer_sl");
  const [rationales, setRationales] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<"queue" | "upload">("queue");
  const [toastMessage, setToastMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Upload modal / state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadAuthority, setUploadAuthority] = useState("Food Control Administration Unit (FCAU)");
  const [uploadInstrument, setUploadInstrument] = useState("regulation");
  const [uploadGazetteNo, setUploadGazetteNo] = useState("");
  const [uploadPubDate, setUploadPubDate] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    try {
      const items = await getPendingReviews();
      setReviews(items);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load review queue.";
      setToastMessage({ type: "error", text: msg });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const showToast = (text: string, type: "success" | "error" = "success") => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 5000);
  };

  const handleApprove = async (ruleId: string) => {
    setActionInProgress(ruleId);
    try {
      const rationale = rationales[ruleId] || "Grounding in statutory source text verified and deterministic Kleene logic approved.";
      const res = await approveReview(ruleId, {
        reviewer_id: reviewerId,
        rationale: rationale,
      });
      showToast(`Rule ${res.rule_id} successfully APPROVED. Audit record created.`);
      setReviews((prev) => prev.filter((r) => r.rule_id !== ruleId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to approve rule.";
      showToast(msg, "error");
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReject = async (ruleId: string) => {
    setActionInProgress(ruleId);
    try {
      const rationale = rationales[ruleId] || "Extracted logic does not accurately reflect statutory intent or coverage constraints.";
      const res = await rejectReview(ruleId, {
        reviewer_id: reviewerId,
        rationale: rationale,
      });
      showToast(`Rule ${res.rule_id} marked as REJECTED. Recorded in audit trail.`);
      setReviews((prev) => prev.filter((r) => r.rule_id !== ruleId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reject rule.";
      showToast(msg, "error");
    } finally {
      setActionInProgress(null);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      showToast("Please select a PDF gazette file to upload.", "error");
      return;
    }
    setUploading(true);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      if (uploadTitle) formData.append("title", uploadTitle);
      if (uploadAuthority) formData.append("authority", uploadAuthority);
      if (uploadInstrument) formData.append("instrument_type", uploadInstrument);
      if (uploadGazetteNo) formData.append("gazette_no", uploadGazetteNo);
      if (uploadPubDate) formData.append("publication_date", uploadPubDate);

      const res = await uploadDocument(formData);
      setUploadResult(`Uploaded successfully! Document ID: ${res.doc_id} (${res.pages_indexed} pages indexed, ${res.rules_compiled} candidate rules extracted).`);
      showToast(`Document ${res.doc_id} ingested! Candidate rules queued for review.`);
      setUploadFile(null);
      setUploadTitle("");
      setUploadGazetteNo("");
      setUploadPubDate("");
      fetchQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload document.";
      showToast(msg, "error");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Banner Toast */}
      {toastMessage && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-xl border shadow-2xl backdrop-blur-md transition-all duration-300 ${
            toastMessage.type === "success"
              ? "bg-emerald-950/90 border-emerald-500/40 text-emerald-200"
              : "bg-rose-950/90 border-rose-500/40 text-rose-200"
          }`}
        >
          {toastMessage.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
          <span className="text-xs font-medium">{toastMessage.text}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 text-slate-400 hover:text-white transition-colors"
          >
            ×
          </button>
        </div>
      )}

      {/* Navigation Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700/60 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Impact Engine</span>
            </Link>

            <div className="h-5 w-px bg-slate-800" />

            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Scale className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>Legal Reviewer & Ingestion Portal</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    Phase 2 & 3 HITL
                  </span>
                </h1>
                <p className="text-[11px] text-slate-400">
                  Dual-Pass LLM Extraction Verification & Statutory Corpus Management
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/evaluation"
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-xs text-indigo-300 border border-indigo-500/30 transition-colors"
            >
              <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Evaluation Dashboard</span>
            </Link>

            <button
              onClick={fetchQueue}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh Queue</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-6">
        {/* Reviewer Context and Tab Navigation */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-slate-900/90 border border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-300">Active Legal Officer:</span>
                <input
                  type="text"
                  value={reviewerId}
                  onChange={(e) => setReviewerId(e.target.value)}
                  className="px-2.5 py-1 bg-slate-950 border border-slate-700 rounded-lg text-xs font-mono text-emerald-400 focus:outline-none focus:border-indigo-500"
                  placeholder="Reviewer ID"
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                All decisions create an immutable cryptographic entry in the <span className="font-mono text-slate-400">human_review_audit</span> table.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("queue")}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium transition-all ${
                activeTab === "queue"
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm"
                  : "bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <FileCheck className="w-4 h-4" />
              <span>Pending Queue ({reviews.length})</span>
            </button>

            <button
              onClick={() => setActiveTab("upload")}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium transition-all ${
                activeTab === "upload"
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm"
                  : "bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <UploadCloud className="w-4 h-4" />
              <span>Upload Gazette PDF</span>
            </button>
          </div>
        </div>

        {/* TAB 1: REVIEW QUEUE */}
        {activeTab === "queue" && (
          <div className="space-y-6">
            {loading ? (
              <div className="p-16 text-center rounded-2xl bg-slate-900/40 border border-slate-800/80">
                <RefreshCw className="w-8 h-8 text-amber-400 animate-spin mx-auto mb-3" />
                <p className="text-sm text-slate-400">Fetching pending candidate rules from database...</p>
              </div>
            ) : reviews.length === 0 ? (
              <div className="p-16 text-center rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-4">
                <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center mx-auto">
                  <Check className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">Review Queue is Clear</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                    All candidate rules compiled from Sri Lankan gazettes have been verified and signed off.
                    Upload a new gazette PDF to trigger automated clause segmentation and LLM rule compilation.
                  </p>
                </div>
                <button
                  onClick={() => setActiveTab("upload")}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors cursor-pointer"
                >
                  <UploadCloud className="w-4 h-4" />
                  <span>Upload Gazette PDF</span>
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="text-xs text-slate-400 flex items-center justify-between">
                  <span>Displaying <strong>{reviews.length}</strong> candidate rules requiring legal sign-off</span>
                  <span className="text-[11px] text-amber-400/80 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> Awaiting adjudication
                  </span>
                </div>

                {reviews.map((rule) => {
                  const currentRationale = rationales[rule.rule_id] ?? "";
                  const isProcessing = actionInProgress === rule.rule_id;

                  return (
                    <div
                      key={rule.rule_id}
                      className="rounded-2xl bg-slate-900/70 border border-slate-800 overflow-hidden shadow-xl hover:border-slate-700/80 transition-all"
                    >
                      {/* Rule Header Bar */}
                      <div className="p-4 sm:p-5 bg-slate-850/60 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                            {rule.rule_id}
                          </span>
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm font-semibold text-white">
                                {rule.clause_number || rule.clause_id}
                              </h3>
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                                {rule.review_status}
                              </span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                {rule.outcome_type}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 mt-0.5">
                              Document: <span className="font-medium text-slate-300">{rule.document_id || "Sri Lanka Gazette"}</span>
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-slate-400 font-mono">Clause: {rule.clause_id}</span>
                        </div>
                      </div>

                      {/* Side-by-Side Verification Grid */}
                      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-800">
                        {/* LEFT COLUMN: Extracted JSON Logic */}
                        <div className="p-5 space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                              <Code2 className="w-4 h-4" />
                              <span>Extracted Neuro-Symbolic Logic</span>
                            </span>
                            <span className="text-[10px] text-slate-500">Dual-Pass Cross-Agreement</span>
                          </div>

                          <div className="space-y-3">
                            {/* Applicability Condition */}
                            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
                                Applicability Condition (applies_if)
                              </span>
                              <pre className="text-xs font-mono text-emerald-300 overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(rule.applies_if, null, 2)}
                              </pre>
                            </div>

                            {/* Obligation */}
                            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
                                Obligation
                              </span>
                              <pre className="text-xs font-mono text-sky-300 overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(rule.obligation, null, 2)}
                              </pre>
                            </div>

                            {/* Validity & Temporal Window */}
                            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
                                Validity & Temporal Enforcement
                              </span>
                              <pre className="text-xs font-mono text-amber-300 overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(rule.validity, null, 2)}
                              </pre>
                            </div>

                            {/* Exceptions */}
                            {rule.exceptions && rule.exceptions.length > 0 && (
                              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
                                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
                                  Exceptions ({rule.exceptions.length})
                                </span>
                                <pre className="text-xs font-mono text-rose-300 overflow-x-auto whitespace-pre-wrap">
                                  {JSON.stringify(rule.exceptions, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* RIGHT COLUMN: Verbatim Quote Span & Source Evidence */}
                        <div className="p-5 space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                              <FileText className="w-4 h-4" />
                              <span>Verbatim Statutory Evidence</span>
                            </span>
                            <span className="text-[10px] text-slate-500">Official Sri Lankan Gazette</span>
                          </div>

                          {/* Verbatim quote span */}
                          <div className="space-y-2">
                            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                              Verbatim Grounding Quote Span
                            </span>
                            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 text-xs text-amber-200/90 leading-relaxed italic relative">
                              <span className="text-amber-500/40 text-3xl font-serif absolute top-1 left-2 select-none">&ldquo;</span>
                              <p className="pl-4">
                                {rule.quote_span ||
                                  (typeof rule.source === "object" && rule.source?.quote_span
                                    ? String(rule.source.quote_span)
                                    : "No direct quote span provided.")}
                              </p>
                            </div>
                          </div>

                          {/* Full Clause Context */}
                          {rule.clause_text && (
                            <div className="space-y-2">
                              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                                Complete Segmented Clause Context
                              </span>
                              <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-300 font-serif leading-relaxed max-h-56 overflow-y-auto whitespace-pre-wrap">
                                {rule.clause_text}
                              </div>
                            </div>
                          )}

                          {/* Provenance Metadata Table */}
                          <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 text-[11px] space-y-1.5">
                            <div className="flex justify-between text-slate-400">
                              <span>Source Instrument:</span>
                              <span className="text-slate-200 font-medium">
                                {typeof rule.source === "object" && rule.source?.instrument
                                  ? String(rule.source.instrument)
                                  : rule.document_id || "Gazette"}
                              </span>
                            </div>
                            <div className="flex justify-between text-slate-400">
                              <span>Statutory Clause:</span>
                              <span className="text-slate-200 font-mono">
                                {rule.clause_number || rule.clause_id}
                              </span>
                            </div>
                            <div className="flex justify-between text-slate-400">
                              <span>Extraction Engine:</span>
                              <span className="text-indigo-400 font-mono">Dual-Pass Self-Consistency (GPT-4o / Claude 3.5 Sonnet)</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Action & Adjudication Controls Bar */}
                      <div className="p-4 sm:p-5 bg-slate-900 border-t border-slate-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                        <div className="flex-1">
                          <input
                            type="text"
                            placeholder="Add optional reviewer rationale or amendments notes..."
                            value={currentRationale}
                            onChange={(e) =>
                              setRationales((prev) => ({ ...prev, [rule.rule_id]: e.target.value }))
                            }
                            className="w-full px-3 py-2 bg-slate-950 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                          />
                        </div>

                        <div className="flex items-center gap-2 justify-end">
                          <button
                            onClick={() => handleReject(rule.rule_id)}
                            disabled={isProcessing}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-950/50 hover:bg-rose-900/60 text-rose-300 border border-rose-700/60 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                          >
                            <XCircle className="w-4 h-4 text-rose-400" />
                            <span>{isProcessing ? "Processing..." : "Reject Rule"}</span>
                          </button>

                          <button
                            onClick={() => handleApprove(rule.rule_id)}
                            disabled={isProcessing}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-950/50 transition-all disabled:opacity-50 cursor-pointer"
                          >
                            <CheckCircle2 className="w-4 h-4 text-white" />
                            <span>{isProcessing ? "Processing..." : "Approve & Certify"}</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: DOCUMENT UPLOAD */}
        {activeTab === "upload" && (
          <div className="max-w-2xl mx-auto rounded-2xl bg-slate-900/80 border border-slate-800 p-6 sm:p-8 space-y-6">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-indigo-400" />
                <span>Ingest Official Sri Lankan Regulatory Document</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Upload a newly published Gazette Extraordinary or Ministerial Direction PDF.
                The system will automatically store the file, extract text, segment clauses, compute embeddings,
                and compile candidate rules using the live LLM client.
              </p>
            </div>

            {uploadResult && (
              <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{uploadResult}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              {/* File Picker */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Official Gazette PDF File *
                </label>
                <div className="border-2 border-dashed border-slate-700 hover:border-indigo-500/80 rounded-xl p-6 text-center transition-colors bg-slate-950/50">
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setUploadFile(e.target.files[0]);
                      }
                    }}
                    className="hidden"
                    id="gazette-file-input"
                  />
                  <label htmlFor="gazette-file-input" className="cursor-pointer block">
                    <FileText className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                    {uploadFile ? (
                      <div className="text-xs">
                        <span className="font-semibold text-indigo-300">{uploadFile.name}</span>
                        <span className="text-slate-500 block mt-0.5">
                          {(uploadFile.size / 1024 / 1024).toFixed(2)} MB
                        </span>
                      </div>
                    ) : (
                      <div className="text-xs text-slate-400">
                        <span className="font-semibold text-indigo-400">Click to browse</span> or drag and drop PDF
                        <p className="text-[11px] text-slate-500 mt-1">Sri Lanka Gazette Extraordinary (Sinhala, Tamil, English PDF)</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Title */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Document / Regulation Title
                </label>
                <input
                  type="text"
                  placeholder="e.g. Food (Labelling and Advertising) Regulations 2024"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Authority & Instrument Type */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Regulatory Authority
                  </label>
                  <select
                    value={uploadAuthority}
                    onChange={(e) => setUploadAuthority(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="Food Control Administration Unit (FCAU)">Food Control Administration Unit (FCAU)</option>
                    <option value="Central Environmental Authority (CEA)">Central Environmental Authority (CEA)</option>
                    <option value="Consumer Affairs Authority (CAA)">Consumer Affairs Authority (CAA)</option>
                    <option value="Sri Lanka Standards Institution (SLSI)">Sri Lanka Standards Institution (SLSI)</option>
                    <option value="Government of Sri Lanka">Government of Sri Lanka (Gazette)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Instrument Type
                  </label>
                  <select
                    value={uploadInstrument}
                    onChange={(e) => setUploadInstrument(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="regulation">Regulation</option>
                    <option value="act">Act / Statute</option>
                    <option value="direction">Ministerial Direction</option>
                    <option value="gazette">Gazette Extraordinary</option>
                  </select>
                </div>
              </div>

              {/* Gazette No & Date */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Gazette Number (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Gazette Extraordinary No. 2380/14"
                    value={uploadGazetteNo}
                    onChange={(e) => setUploadGazetteNo(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Publication Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={uploadPubDate}
                    onChange={(e) => setUploadPubDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg shadow-indigo-950/50 transition-all disabled:opacity-50 cursor-pointer"
                >
                  <UploadCloud className={`w-4 h-4 ${uploading ? "animate-bounce" : ""}`} />
                  <span>{uploading ? "Ingesting & Compiling Rules..." : "Ingest Document & Compile Rules"}</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
