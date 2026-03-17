"use client";

import { useState } from "react";
import { useDatasetStore } from "@/stores/datasetStore";
import { filesApi, exportApi } from "@/lib/api";
import { toast } from "sonner";

// Dialog imports
import { FrequenciesDialog } from "@/components/Dialogs/FrequenciesDialog";
import { DescriptivesDialog } from "@/components/Dialogs/DescriptivesDialog";
import { CrosstabsDialog } from "@/components/Dialogs/CrosstabsDialog";
import { ExploreDialog } from "@/components/Dialogs/ExploreDialog";
import { IndependentTTestDialog } from "@/components/Dialogs/IndependentTTestDialog";
import { PairedTTestDialog } from "@/components/Dialogs/PairedTTestDialog";
import { OneSampleTTestDialog } from "@/components/Dialogs/OneSampleTTestDialog";
import { OneWayAnovaDialog } from "@/components/Dialogs/OneWayAnovaDialog";
import { MeansDialog } from "@/components/Dialogs/MeansDialog";
import { CorrelationDialog } from "@/components/Dialogs/CorrelationDialog";
import { LinearRegressionDialog } from "@/components/Dialogs/LinearRegressionDialog";
import { LogisticRegressionDialog } from "@/components/Dialogs/LogisticRegressionDialog";
import { FactorAnalysisDialog } from "@/components/Dialogs/FactorAnalysisDialog";
import { ReliabilityDialog } from "@/components/Dialogs/ReliabilityDialog";
import { RecodeDialog } from "@/components/Dialogs/RecodeDialog";
import { ComputeDialog } from "@/components/Dialogs/ComputeDialog";
import { SortDialog } from "@/components/Dialogs/SortDialog";

type DialogName =
  | "frequencies" | "descriptives" | "crosstabs" | "explore"
  | "ttest-independent" | "ttest-paired" | "ttest-onesample"
  | "anova-oneway" | "means"
  | "correlation" | "linear-regression" | "logistic-regression"
  | "factor" | "reliability"
  | "recode" | "compute" | "sort"
  | null;

interface MenuBarProps {
  onShowOutput: () => void;
}

interface MenuItem {
  label: string;
  dialog?: DialogName;
  action?: () => void;
  separator?: boolean;
}

interface Menu {
  label: string;
  items: MenuItem[];
}

export function MenuBar({ onShowOutput }: MenuBarProps) {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState<DialogName>(null);
  const { sessionId, outputBlocks, clearSession, clearOutputBlocks } = useDatasetStore();

  const closeDialog = () => setOpenDialog(null);
  const openD = (d: DialogName) => { setOpenDialog(d); setActiveMenu(null); };

  const handleExportPDF = async () => {
    setActiveMenu(null);
    if (outputBlocks.length === 0) { toast.error("No output to export"); return; }
    try {
      const blob = await exportApi.pdf({ output_blocks: outputBlocks });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "bernie-spss-output.pdf"; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { toast.error("PDF export failed"); }
  };

  const handleExportExcel = async () => {
    setActiveMenu(null);
    if (outputBlocks.length === 0) { toast.error("No output to export"); return; }
    try {
      const blob = await exportApi.excel({ output_blocks: outputBlocks });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "bernie-spss-output.xlsx"; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { toast.error("Excel export failed"); }
  };

  const handleExportSav = async () => {
    setActiveMenu(null);
    if (!sessionId) return;
    try {
      const blob = await filesApi.exportSav(sessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "data.sav"; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { toast.error("SAV export failed"); }
  };

  const handleCloseFile = () => {
    setActiveMenu(null);
    clearSession();
    toast.info("Dataset closed");
  };

  const menus: Menu[] = [
    {
      label: "File",
      items: [
        { label: "Open Data…", action: () => { setActiveMenu(null); window.location.reload(); } },
        { separator: true, label: "" },
        { label: "Save Data As (.sav)", action: handleExportSav },
        { label: "Export Output as PDF", action: handleExportPDF },
        { label: "Export Output as Excel", action: handleExportExcel },
        { separator: true, label: "" },
        { label: "Close Dataset", action: handleCloseFile },
      ],
    },
    {
      label: "Analyze",
      items: [
        { label: "── Descriptive Statistics ──", action: () => {} },
        { label: "  Frequencies…", dialog: "frequencies" },
        { label: "  Descriptives…", dialog: "descriptives" },
        { label: "  Explore…", dialog: "explore" },
        { label: "  Crosstabs…", dialog: "crosstabs" },
        { separator: true, label: "" },
        { label: "── Compare Means ──", action: () => {} },
        { label: "  Means…", dialog: "means" },
        { label: "  One-Sample T Test…", dialog: "ttest-onesample" },
        { label: "  Independent-Samples T Test…", dialog: "ttest-independent" },
        { label: "  Paired-Samples T Test…", dialog: "ttest-paired" },
        { label: "  One-Way ANOVA…", dialog: "anova-oneway" },
        { separator: true, label: "" },
        { label: "── Correlate ──", action: () => {} },
        { label: "  Bivariate Correlations…", dialog: "correlation" },
        { separator: true, label: "" },
        { label: "── Regression ──", action: () => {} },
        { label: "  Linear…", dialog: "linear-regression" },
        { label: "  Binary Logistic…", dialog: "logistic-regression" },
        { separator: true, label: "" },
        { label: "── Dimension Reduction ──", action: () => {} },
        { label: "  Factor Analysis…", dialog: "factor" },
        { separator: true, label: "" },
        { label: "── Scale ──", action: () => {} },
        { label: "  Reliability Analysis…", dialog: "reliability" },
      ],
    },
    {
      label: "Transform",
      items: [
        { label: "Compute Variable…", dialog: "compute" },
        { label: "Recode into Different Variables…", dialog: "recode" },
        { separator: true, label: "" },
        { label: "Sort Cases…", dialog: "sort" },
      ],
    },
    {
      label: "View",
      items: [
        { label: "Output Viewer", action: () => { setActiveMenu(null); onShowOutput(); } },
        { separator: true, label: "" },
        { label: "Clear Output", action: () => { setActiveMenu(null); clearOutputBlocks(); toast.info("Output cleared"); } },
      ],
    },
  ];

  return (
    <>
      {/* Menu Bar */}
      <div className="flex items-center bg-gray-200 border-b border-gray-400 px-1 py-0.5 select-none">
        {/* Logo/App Name */}
        <span className="text-xs font-bold text-spss-blue px-3 py-1 mr-2">SOTA StatWorks</span>

        {menus.map((menu) => (
          <div key={menu.label} className="relative">
            <button
              className={`px-3 py-1 text-xs rounded transition-colors ${
                activeMenu === menu.label
                  ? "bg-white border border-gray-400 shadow-sm"
                  : "hover:bg-gray-300"
              } ${!sessionId && menu.label !== "File" ? "opacity-40 cursor-not-allowed" : ""}`}
              onClick={() => {
                if (!sessionId && menu.label !== "File") return;
                setActiveMenu(activeMenu === menu.label ? null : menu.label);
              }}
            >
              {menu.label}
            </button>

            {activeMenu === menu.label && (
              <>
                {/* Backdrop */}
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setActiveMenu(null)}
                />
                {/* Dropdown */}
                <div className="absolute left-0 top-full z-50 bg-white border border-gray-300 shadow-lg rounded min-w-[220px] py-1">
                  {menu.items.map((item, i) => {
                    if (item.separator) {
                      return <hr key={i} className="border-gray-200 my-1" />;
                    }
                    const isHeader = item.label.startsWith("──");
                    if (isHeader) {
                      return (
                        <div key={i} className="px-3 py-1 text-[10px] text-gray-400 font-semibold uppercase tracking-wide">
                          {item.label.replace(/──\s*/g, "").replace(/\s*──/g, "")}
                        </div>
                      );
                    }
                    return (
                      <button
                        key={i}
                        className="w-full text-left px-4 py-1.5 text-xs hover:bg-blue-600 hover:text-white transition-colors"
                        onClick={() => {
                          if (item.dialog) openD(item.dialog);
                          else if (item.action) item.action();
                        }}
                      >
                        {item.label.trim()}
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        ))}

        {/* Status bar right side */}
        {sessionId && (
          <div className="ml-auto pr-3 text-[10px] text-gray-500">
            Session active
          </div>
        )}
      </div>

      {/* Dialogs */}
      <FrequenciesDialog open={openDialog === "frequencies"} onClose={closeDialog} />
      <DescriptivesDialog open={openDialog === "descriptives"} onClose={closeDialog} />
      <CrosstabsDialog open={openDialog === "crosstabs"} onClose={closeDialog} />
      <ExploreDialog open={openDialog === "explore"} onClose={closeDialog} />
      <IndependentTTestDialog open={openDialog === "ttest-independent"} onClose={closeDialog} />
      <PairedTTestDialog open={openDialog === "ttest-paired"} onClose={closeDialog} />
      <OneSampleTTestDialog open={openDialog === "ttest-onesample"} onClose={closeDialog} />
      <OneWayAnovaDialog open={openDialog === "anova-oneway"} onClose={closeDialog} />
      <MeansDialog open={openDialog === "means"} onClose={closeDialog} />
      <CorrelationDialog open={openDialog === "correlation"} onClose={closeDialog} />
      <LinearRegressionDialog open={openDialog === "linear-regression"} onClose={closeDialog} />
      <LogisticRegressionDialog open={openDialog === "logistic-regression"} onClose={closeDialog} />
      <FactorAnalysisDialog open={openDialog === "factor"} onClose={closeDialog} />
      <ReliabilityDialog open={openDialog === "reliability"} onClose={closeDialog} />
      <RecodeDialog open={openDialog === "recode"} onClose={closeDialog} />
      <ComputeDialog open={openDialog === "compute"} onClose={closeDialog} />
      <SortDialog open={openDialog === "sort"} onClose={closeDialog} />
    </>
  );
}
