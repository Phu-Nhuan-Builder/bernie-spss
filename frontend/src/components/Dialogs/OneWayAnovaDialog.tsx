"use client";
import { useState } from "react";
import { useDatasetStore } from "@/stores/datasetStore";
import { testsApi } from "@/lib/api";
import { toast } from "sonner";

interface Props { open: boolean; onClose: () => void; }

export function OneWayAnovaDialog({ open, onClose }: Props) {
  const { sessionId, metadata, addOutputBlock } = useDatasetStore();
  const [depVar, setDepVar] = useState("");
  const [factorVar, setFactorVar] = useState("");
  const [posthoc, setPosthoc] = useState("tukey");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const numericVars = metadata?.variables.filter((v) => v.var_type === "numeric");
  const catVars = metadata?.variables.filter((v) => v.measure !== "scale");

  const handleRun = async () => {
    if (!sessionId || !depVar || !factorVar) { toast.error("Select dependent and factor variables"); return; }
    setLoading(true);
    try {
      const result = await testsApi.oneWayAnova({ session_id: sessionId, dep_var: depVar, group_var: factorVar, posthoc });
      addOutputBlock({
        id: crypto.randomUUID(),
        type: "table",
        title: `One-Way ANOVA — ${depVar} by ${factorVar}`,
        content: result,
        created_at: new Date(),
        procedure: "anova-oneway",
      });
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white border border-gray-300 shadow-xl rounded w-80 p-4">
        <h3 className="font-bold text-sm mb-3">One-Way ANOVA</h3>
        <div className="mb-2">
          <label className="text-xs text-gray-600 block mb-1">Dependent variable:</label>
          <select className="w-full border border-gray-300 rounded px-2 py-1 text-sm" value={depVar} onChange={(e) => setDepVar(e.target.value)}>
            <option value="">-- Select --</option>
            {numericVars?.map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
          </select>
        </div>
        <div className="mb-2">
          <label className="text-xs text-gray-600 block mb-1">Factor (grouping variable):</label>
          <select className="w-full border border-gray-300 rounded px-2 py-1 text-sm" value={factorVar} onChange={(e) => setFactorVar(e.target.value)}>
            <option value="">-- Select --</option>
            {catVars?.filter((v) => v.name !== depVar).map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
          </select>
        </div>
        <div className="mb-4">
          <label className="text-xs text-gray-600 block mb-1">Post-hoc test:</label>
          <select className="w-full border border-gray-300 rounded px-2 py-1 text-sm" value={posthoc} onChange={(e) => setPosthoc(e.target.value)}>
            <option value="tukey">Tukey HSD</option>
            <option value="bonferroni">Bonferroni</option>
            <option value="scheffe">Scheffé</option>
            <option value="lsd">LSD</option>
            <option value="none">None</option>
          </select>
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50">Cancel</button>
          <button onClick={handleRun} disabled={loading} className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">{loading ? "Running..." : "OK"}</button>
        </div>
      </div>
    </div>
  );
}
