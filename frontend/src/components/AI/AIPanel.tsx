"use client";

import { useState, useCallback } from "react";
import { useDatasetStore } from "@/stores/datasetStore";
import { aiApi } from "@/lib/api";
import { toast } from "sonner";
import {
  Brain,
  Sparkles,
  FileText,
  Send,
  Loader2,
  ChevronRight,
  Lightbulb,
} from "lucide-react";
import type { AIAnalyzeResponse, AIAutoResponse, AIReportResponse, OutputBlock } from "@/types/dataset";

export function AIPanel() {
  const { sessionId, addOutputBlock } = useDatasetStore();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState<"analyze" | "auto" | "report" | null>(null);

  const addAIOutput = useCallback(
    (title: string, subtitle: string, content: unknown, procedure: string, type: "ai-insight" | "ai-report" = "ai-insight") => {
      const block: OutputBlock = {
        id: `ai-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        type,
        title,
        subtitle,
        content,
        created_at: new Date(),
        procedure,
      };
      addOutputBlock(block);
    },
    [addOutputBlock]
  );

  const handleAnalyze = useCallback(async () => {
    if (!sessionId || !query.trim()) return;
    setLoading("analyze");
    try {
      const result: AIAnalyzeResponse = await aiApi.analyze(sessionId, query.trim());
      if (result.status === "error") {
        toast.error(result.message || "Analysis failed");
        return;
      }
      addAIOutput(
        `🧠 AI Analysis: "${query.trim()}"`,
        String(result.plan?.description ?? ""),
        result,
        "ai-analyze"
      );
      toast.success(result.insight?.headline || "Analysis complete");
      setQuery("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(null);
    }
  }, [sessionId, query, addAIOutput]);

  const handleAutoAnalyze = useCallback(async () => {
    if (!sessionId) return;
    setLoading("auto");
    try {
      const result: AIAutoResponse = await aiApi.analyzeAuto(sessionId);
      if (result.status === "error") {
        toast.error(result.message || "Auto-analysis failed");
        return;
      }
      addAIOutput(
        `🚀 Auto Analysis — ${result.n_analyses} analyses`,
        "Full dataset analysis with AI insights",
        result,
        "ai-auto-analyze"
      );
      toast.success(`Completed ${result.n_analyses} analyses`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Auto-analysis failed");
    } finally {
      setLoading(null);
    }
  }, [sessionId, addAIOutput]);

  const handleReport = useCallback(async () => {
    if (!sessionId) return;
    setLoading("report");
    try {
      const result: AIReportResponse = await aiApi.generateReport(sessionId);
      if (result.status === "error") {
        toast.error(result.message || "Report generation failed");
        return;
      }
      addAIOutput(
        `📄 ${result.report?.title || "Statistical Report"}`,
        `Based on ${result.n_analyses} analyses`,
        result,
        "ai-report",
        "ai-report"
      );
      toast.success("Report generated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setLoading(null);
    }
  }, [sessionId, addAIOutput]);

  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
        <Brain className="w-12 h-12 text-gray-300" />
        <p className="text-sm">Upload a dataset to use AI analysis</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-900 via-blue-800 to-cyan-700 text-white px-6 py-4">
        <div className="flex items-center gap-2 mb-1">
          <Brain className="w-5 h-5" />
          <h2 className="text-sm font-bold tracking-wide">SOTA StatWorks AI</h2>
        </div>
        <p className="text-xs text-blue-200">
          Ask questions in natural language or let AI analyze your data automatically
        </p>
      </div>

      {/* Query Input */}
      <div className="p-4 bg-white border-b border-gray-200">
        <label className="text-xs font-semibold text-gray-600 mb-2 block">
          Ask a question about your data
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAnalyze();
              }
            }}
            placeholder='e.g. "Compare groups" or "What affects sales?"'
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
            disabled={loading !== null}
          />
          <button
            onClick={handleAnalyze}
            disabled={loading !== null || !query.trim()}
            className="px-4 py-2 bg-blue-800 text-white text-sm font-medium rounded-lg hover:bg-blue-900 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-1.5"
          >
            {loading === "analyze" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            Analyze
          </button>
        </div>

        {/* Example queries */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {[
            "Compare two groups",
            "Find correlations",
            "What predicts the outcome?",
            "Check normality",
          ].map((example) => (
            <button
              key={example}
              onClick={() => setQuery(example)}
              className="text-[11px] px-2.5 py-1 bg-gray-100 text-gray-600 rounded-full hover:bg-blue-50 hover:text-blue-700 transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="p-4 space-y-3">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Quick Actions
        </h3>

        {/* Analyze for me */}
        <button
          onClick={handleAutoAnalyze}
          disabled={loading !== null}
          className="w-full flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0">
            {loading === "auto" ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <Sparkles className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="text-left flex-1">
            <span className="text-sm font-semibold text-gray-800 group-hover:text-blue-800 transition-colors block">
              🧠 Analyze for me
            </span>
            <span className="text-xs text-gray-500">
              Full autonomous analysis — descriptives, correlations, comparisons, regression
            </span>
          </div>
          <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600 transition-colors" />
        </button>

        {/* Generate Report */}
        <button
          onClick={handleReport}
          disabled={loading !== null}
          className="w-full flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-teal-400 to-emerald-600 flex items-center justify-center flex-shrink-0">
            {loading === "report" ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <FileText className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="text-left flex-1">
            <span className="text-sm font-semibold text-gray-800 group-hover:text-blue-800 transition-colors block">
              📄 Generate Report
            </span>
            <span className="text-xs text-gray-500">
              Academic-style report: Introduction → Methodology → Results → Discussion
            </span>
          </div>
          <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600 transition-colors" />
        </button>
      </div>

      {/* Info */}
      <div className="mt-auto p-4">
        <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-100 rounded-lg">
          <Lightbulb className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-blue-800">
            <strong>Tip:</strong> Results appear in the Output Viewer tab.
            Use natural language in English or Vietnamese — the AI understands both.
          </div>
        </div>

        {loading !== null && (
          <div className="flex items-center gap-2 mt-3 p-3 bg-amber-50 border border-amber-100 rounded-lg">
            <Loader2 className="w-4 h-4 text-amber-600 animate-spin flex-shrink-0" />
            <span className="text-xs text-amber-800">
              AI is analyzing your data… This may take 10-30 seconds.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
