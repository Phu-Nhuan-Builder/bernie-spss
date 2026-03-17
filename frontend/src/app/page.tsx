"use client";

import { useState, useCallback } from "react";
import { useDatasetStore } from "@/stores/datasetStore";
import { filesApi } from "@/lib/api";
import { toast } from "sonner";
import { SPSSWorkbench } from "@/components/SPSSWorkbench";
import { Upload, BarChart2, FileText, Database, Brain, Sparkles } from "lucide-react";

export default function HomePage() {
  const { sessionId, setSession } = useDatasetStore();
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      const allowed = [".sav", ".csv", ".xlsx", ".xls"];
      const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
      if (!allowed.includes(ext)) {
        toast.error(`Unsupported file type: ${ext}. Please upload .sav, .csv, or .xlsx`);
        return;
      }
      setUploading(true);
      try {
        const session = await filesApi.upload(file);
        setSession(session.session_id, session.meta);
        toast.success(`Loaded: ${session.meta.file_name} (${session.meta.n_cases} cases, ${session.meta.n_vars} variables)`);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [setSession]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  if (sessionId) {
    return <SPSSWorkbench />;
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-2">
          <BarChart2 className="w-10 h-10 text-spss-blue" />
          <h1 className="text-3xl font-bold text-spss-blue tracking-tight">SOTA StatWorks</h1>
        </div>
        <p className="text-gray-500 text-sm">
          AI-native statistical analysis platform — powered by natural language
        </p>
      </div>

      {/* Upload Card */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-md w-full max-w-lg p-8">
        <h2 className="text-base font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Database className="w-4 h-4" />
          Open a Dataset
        </h2>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-10 text-center transition-colors ${
            dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-gray-400"
          }`}
        >
          <Upload className="w-8 h-8 mx-auto text-gray-400 mb-3" />
          <p className="text-sm text-gray-600 mb-1">
            {uploading ? "Uploading…" : "Drag & drop your file here"}
          </p>
          <p className="text-xs text-gray-400 mb-4">Supports .sav, .csv, .xlsx</p>
          <label className="cursor-pointer">
            <span className="inline-block px-4 py-2 bg-spss-blue text-white text-sm rounded hover:bg-blue-900 transition-colors">
              {uploading ? "Please wait…" : "Browse File"}
            </span>
            <input
              type="file"
              className="hidden"
              accept=".sav,.csv,.xlsx,.xls"
              onChange={handleInputChange}
              disabled={uploading}
            />
          </label>
        </div>

        {/* Feature list */}
        <div className="mt-6 grid grid-cols-2 gap-3">
          {[
            { icon: Brain, label: "🧠 AI-Powered Analysis" },
            { icon: Sparkles, label: "One-Click Auto-Analyze" },
            { icon: FileText, label: "Frequencies & Descriptives" },
            { icon: BarChart2, label: "T-Tests & ANOVA" },
            { icon: BarChart2, label: "Correlation & Regression" },
            { icon: BarChart2, label: "Factor & Reliability" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-2 text-xs text-gray-500">
              <Icon className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <span>{label}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-6 text-xs text-gray-400">
        SOTA StatWorks v1.0 — AI-native statistical analysis
      </p>
    </div>
  );
}
