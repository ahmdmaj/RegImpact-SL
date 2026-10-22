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
import { Navbar } from "@/components/Navbar";
import { formatGazetteTitle } from "@/components/StatutoryCitationCard";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  UploadCloud,
  FileText,
  RefreshCw,
  Scale,
  Code2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  FolderOpen
} from "lucide-react";

export default function AdminReviewsPage() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [reviewerId, setReviewerId] = useState("legal_officer_sl");
  const [rationales, setRationales] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<"queue" | "upload">("queue");
  const [expandedRawJson, setExpandedRawJson] = useState<Record<string, boolean>>({});
  const [toastMessage, setToastMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Upload state
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
      showToast(`Rule ${res.rule_id} successfully approved. Immutable audit record created.`);
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
      showToast(`Rule ${res.rule_id} marked REJECTED.`);
      setReviews((prev) => prev.filter((r) => r.rule_id !== ruleId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reject rule.";
      showToast(msg, "error");
    } finally {
      setActionInProgress(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      showToast("Please choose a PDF file to upload.", "error");
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

  const toggleRawJson = (ruleId: string) => {
    setExpandedRawJson((prev) => ({ ...prev, [ruleId]: !prev[ruleId] }));
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-zinc-800 selection:text-white">
      {/* Toast Alert */}
      {toastMessage && (
        <div
          className={`fixed top-20 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg border shadow-lg text-xs font-medium transition-all ${
            toastMessage.type === "success"
              ? "bg-zinc-900 border-emerald-800/60 text-emerald-300"
              : "bg-zinc-900 border-rose-800/60 text-rose-300"
          }`}
        >
          {toastMessage.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 text-zinc-400 hover:text-white"
          >
            &times;
          </button>
        </div>
      )}

      {/* 1. Global Navigation Bar */}
      <Navbar />

      {/* 2. Main Workspace */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-6">
        {/* Top Control Bar: Active Reviewer & Tab Toggle */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl border border-zinc-800 bg-zinc-900 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-zinc-800 text-zinc-200 border border-zinc-700">
              <Scale className="w-5 h-5 text-zinc-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-zinc-100">
                  Legal Reviewer & Adjudication Portal
                </h1>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                  Human-In-The-Loop Audit
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-zinc-400">Reviewer ID:</span>
                <input
                  type="text"
                  value={reviewerId}
                  onChange={(e) => setReviewerId(e.target.value)}
                  className="px-2 py-0.5 bg-zinc-950 border border-zinc-800 rounded text-xs font-mono text-zinc-200 focus:outline-none focus:border-zinc-500"
                  placeholder="Reviewer ID"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("queue")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                activeTab === "queue"
                  ? "bg-zinc-800 text-zinc-100 border border-zinc-700 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              Review Queue ({reviews.length})
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                activeTab === "upload"
                  ? "bg-zinc-800 text-zinc-100 border border-zinc-700 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              Ingest Document (PDF)
            </button>
            <button
              onClick={fetchQueue}
              disabled={loading}
              className="p-1.5 rounded-lg bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-700 transition-colors ml-1 cursor-pointer"
              title="Refresh queue"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* TAB 1: REVIEW QUEUE */}
        {activeTab === "queue" && (
          <div className="space-y-4">
            {loading ? (
              <div className="p-12 text-center text-xs text-zinc-400 rounded-xl border border-zinc-800 bg-zinc-900 space-y-2">
                <div className="w-5 h-5 border-2 border-zinc-700 border-t-zinc-300 rounded-full animate-spin mx-auto" />
                <p>Loading candidate statutory rules from PostgreSQL...</p>
              </div>
            ) : reviews.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-12 text-center space-y-3">
                <div className="w-10 h-10 mx-auto rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-300 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                </div>
                <h3 className="text-sm font-semibold text-zinc-100">Review Queue Empty</h3>
                <p className="text-xs text-zinc-400 max-w-md mx-auto">
                  All candidate statutory clauses have been verified and certified. Upload new Gazette PDFs or trigger seeder to populate.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {reviews.map((rule) => {
                  const isProcessing = actionInProgress === rule.rule_id;
                  const currentRationale = rationales[rule.rule_id] || "";
                  const isRawExpanded = !!expandedRawJson[rule.rule_id];

                  return (
                    <div
                      key={rule.rule_id}
                      className="rounded-xl border border-zinc-800 bg-zinc-900 shadow-sm overflow-hidden"
                    >
                      {/* Card Header */}
                      <div className="p-4 bg-zinc-950/70 border-b border-zinc-800 flex items-center justify-between gap-3 flex-wrap">
                        <div className="flex items-center gap-2.5">
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-800 text-amber-300 border border-zinc-700">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                            PENDING VERIFICATION
                          </span>
                          <span className="text-xs font-semibold text-zinc-100">
                            Rule: {rule.rule_id}
                          </span>
                          <span className="text-xs text-zinc-400">
                            &bull; {formatGazetteTitle(null, rule.document_id)}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono text-zinc-500">
                          Clause: {rule.clause_number || rule.clause_id}
                        </span>
                      </div>

                      {/* Side-by-Side Verification Grid */}
                      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-zinc-800">
                        {/* LEFT COLUMN: Extracted Logic */}
                        <div className="p-5 space-y-3 bg-zinc-900/40">
                          <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
                            <span className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                              <Code2 className="w-3.5 h-3.5 text-zinc-400" />
                              <span>Compiled Rule Logic</span>
                            </span>
                            <button
                              type="button"
                              onClick={() => toggleRawJson(rule.rule_id)}
                              className="text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1 cursor-pointer"
                            >
                              <span>{isRawExpanded ? "Hide JSON" : "Inspect Raw JSON"}</span>
                              {isRawExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            </button>
                          </div>

                          {/* Structured Key Values */}
                          <div className="space-y-2 text-xs">
                            <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                              <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">
                                Applicability Condition (applies_if):
                              </span>
                              <pre className="font-mono text-emerald-400 text-[11px] overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(rule.applies_if, null, 2)}
                              </pre>
                            </div>

                            <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                              <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">
                                Statutory Obligation:
                              </span>
                              <pre className="font-mono text-zinc-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(rule.obligation, null, 2)}
                              </pre>
                            </div>

                            {rule.validity && (
                              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                                <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">
                                  Temporal Enforcement Window:
                                </span>
                                <pre className="font-mono text-amber-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
                                  {JSON.stringify(rule.validity, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Raw JSON Accordion */}
                            {isRawExpanded && (
                              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                                <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">
                                  Full Compiler Payload:
                                </span>
                                <pre className="font-mono text-zinc-400 text-[10px] overflow-x-auto max-h-48 whitespace-pre">
                                  {JSON.stringify(rule, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* RIGHT COLUMN: Verbatim Grounding Quote Span & Evidence */}
                        <div className="p-5 space-y-3 bg-zinc-900/40">
                          <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
                            <span className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5 text-zinc-400" />
                              <span>Verbatim Statutory Grounding</span>
                            </span>
                            <span className="text-[10px] font-mono text-zinc-500">Official Gazette</span>
                          </div>

                          {/* Quote Span in Serif */}
                          <div className="space-y-1">
                            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block">
                              Gazette Excerpt (Grounding Target)
                            </span>
                            <div className="p-3.5 rounded-lg bg-zinc-950 border-l-2 border-amber-500/70 border-r border-t border-b border-zinc-800 text-xs text-zinc-200 legal-quote-text italic leading-relaxed">
                              &ldquo;
                              {rule.quote_span ||
                                (typeof rule.source === "object" && rule.source?.quote_span
                                  ? String(rule.source.quote_span)
                                  : "No direct quote span provided.")}
                              &rdquo;
                            </div>
                          </div>

                          {/* Full Context If Available */}
                          {rule.clause_text && (
                            <div className="space-y-1">
                              <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block">
                                Complete Clause Text
                              </span>
                              <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-300 legal-quote-text leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
                                {rule.clause_text}
                              </div>
                            </div>
                          )}

                          {/* Provenance Metadata Table */}
                          <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-[11px] space-y-1">
                            <div className="flex justify-between text-zinc-400">
                              <span>Statutory Authority:</span>
                              <span className="text-zinc-200 font-medium">
                                {typeof rule.source === "object" && rule.source?.authority
                                  ? String(rule.source.authority)
                                  : "Statutory Authority"}
                              </span>
                            </div>
                            <div className="flex justify-between text-zinc-400">
                              <span>Instrument:</span>
                              <span className="text-zinc-200 font-mono">
                                {typeof rule.source === "object" && rule.source?.instrument
                                  ? String(rule.source.instrument)
                                  : rule.document_id || "Gazette"}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Action Bar */}
                      <div className="p-4 bg-zinc-950 border-t border-zinc-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                        <input
                          type="text"
                          placeholder="Optional legal reviewer rationale / notes..."
                          value={currentRationale}
                          onChange={(e) =>
                            setRationales((prev) => ({ ...prev, [rule.rule_id]: e.target.value }))
                          }
                          className="flex-1 h-9 px-3 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-500"
                        />

                        <div className="flex items-center gap-2 justify-end">
                          <button
                            type="button"
                            onClick={() => handleReject(rule.rule_id)}
                            disabled={isProcessing}
                            className="px-3.5 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-rose-400 border border-zinc-700 text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer"
                          >
                            <span>{isProcessing ? "Processing..." : "Reject"}</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => handleApprove(rule.rule_id)}
                            disabled={isProcessing}
                            className="px-4 py-2 rounded-lg bg-white hover:bg-zinc-200 text-zinc-950 text-xs font-medium shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                          >
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
          <div className="max-w-2xl mx-auto rounded-xl border border-zinc-800 bg-zinc-900 shadow-sm p-6 sm:p-8 space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-zinc-300" />
                <span>Upload Statutory Gazette Document (PDF)</span>
              </h2>
              <p className="text-xs text-zinc-400 mt-1">
                Upload official Sri Lankan Extraordinary Gazettes or Act amendments. The document ingestion service will extract pages, segment clauses, and run LLM compilation.
              </p>
            </div>

            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  PDF Gazette File
                </label>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-zinc-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700 cursor-pointer"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    Official Document Title
                  </label>
                  <input
                    type="text"
                    value={uploadTitle}
                    onChange={(e) => setUploadTitle(e.target.value)}
                    placeholder="e.g. Food (Labelling) Regulations 2024"
                    className="w-full h-10 px-3 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-zinc-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    Gazette Number
                  </label>
                  <input
                    type="text"
                    value={uploadGazetteNo}
                    onChange={(e) => setUploadGazetteNo(e.target.value)}
                    placeholder="e.g. 2443/27"
                    className="w-full h-10 px-3 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-zinc-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    Statutory Authority
                  </label>
                  <select
                    value={uploadAuthority}
                    onChange={(e) => setUploadAuthority(e.target.value)}
                    className="w-full h-10 px-3 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-zinc-500 cursor-pointer"
                  >
                    <option value="Food Control Administration Unit (FCAU)">Food Control Administration Unit (FCAU)</option>
                    <option value="Central Environmental Authority (CEA)">Central Environmental Authority (CEA)</option>
                    <option value="Consumer Affairs Authority (CAA)">Consumer Affairs Authority (CAA)</option>
                    <option value="Sri Lanka Standards Institution (SLSI)">Sri Lanka Standards Institution (SLSI)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                    Publication / Gazette Date
                  </label>
                  <input
                    type="date"
                    value={uploadPubDate}
                    onChange={(e) => setUploadPubDate(e.target.value)}
                    className="w-full h-10 px-3 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-zinc-500 cursor-pointer"
                  />
                </div>
              </div>

              {uploadResult && (
                <div className="p-3 rounded-lg bg-zinc-950 border border-emerald-800/60 text-xs text-emerald-300">
                  {uploadResult}
                </div>
              )}

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="w-full h-10 flex items-center justify-center gap-2 bg-white hover:bg-zinc-200 text-zinc-950 font-medium text-xs rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm cursor-pointer"
                >
                  {uploading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-zinc-900/30 border-t-zinc-900 rounded-full animate-spin" />
                      <span>Ingesting PDF & Compiling Rules...</span>
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4 text-zinc-900" />
                      <span>Upload & Ingest Into Corpus</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-zinc-800 bg-zinc-950 py-4 text-xs text-zinc-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>RegImpact-SL Legal Reviewer Portal</span>
          <span className="font-mono text-[11px] text-zinc-500">Human-In-The-Loop Provenance Audit</span>
        </div>
      </footer>
    </div>
  );
}
