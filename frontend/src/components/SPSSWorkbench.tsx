"use client";

import { useState } from "react";
import { MenuBar } from "@/components/Menus/MenuBar";
import { DataEditorTabs } from "@/components/DataEditor/DataEditorTabs";
import { OutputViewer } from "@/components/Output/OutputViewer";
import { AIPanel } from "@/components/AI/AIPanel";
import { useDatasetStore } from "@/stores/datasetStore";

type ViewMode = "data-editor" | "output" | "ai-analysis";

export function SPSSWorkbench() {
  const [viewMode, setViewMode] = useState<ViewMode>("data-editor");
  const { outputBlocks } = useDatasetStore();

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-200">
      {/* Menu Bar */}
      <MenuBar onShowOutput={() => setViewMode("output")} />

      {/* View Toggle */}
      <div className="flex border-b border-gray-400 bg-gray-100 px-2 pt-1 gap-1">
        <button
          onClick={() => setViewMode("data-editor")}
          className={`px-4 py-1 text-xs rounded-t border border-b-0 transition-colors ${
            viewMode === "data-editor"
              ? "bg-white border-gray-400 font-semibold"
              : "bg-gray-200 border-gray-300 hover:bg-gray-50"
          }`}
        >
          Data Editor
        </button>
        <button
          onClick={() => setViewMode("output")}
          className={`px-4 py-1 text-xs rounded-t border border-b-0 transition-colors relative ${
            viewMode === "output"
              ? "bg-white border-gray-400 font-semibold"
              : "bg-gray-200 border-gray-300 hover:bg-gray-50"
          }`}
        >
          Output Viewer
          {outputBlocks.length > 0 && (
            <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 text-[10px] bg-blue-600 text-white rounded-full">
              {outputBlocks.length > 9 ? "9+" : outputBlocks.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setViewMode("ai-analysis")}
          className={`px-4 py-1 text-xs rounded-t border border-b-0 transition-colors ${
            viewMode === "ai-analysis"
              ? "bg-white border-gray-400 font-semibold"
              : "bg-gray-200 border-gray-300 hover:bg-gray-50"
          }`}
        >
          🧠 AI Analysis
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === "data-editor" ? (
          <DataEditorTabs />
        ) : viewMode === "output" ? (
          <OutputViewer />
        ) : (
          <AIPanel />
        )}
      </div>
    </div>
  );
}
