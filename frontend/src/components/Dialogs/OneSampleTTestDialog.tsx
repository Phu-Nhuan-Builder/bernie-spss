"use client";
import { useState } from "react";
import { useDatasetStore } from "@/stores/datasetStore";
import { testsApi } from "@/lib/api";
import { toast } from "sonner";

interface Props { open: boolean; onClose: () => void; }

export function OneSampleTTestDialog({ open, onClose }: Props) {
  const { sessionId, metadata, addOutputBlock } = useDatasetStore();
  const [testVar, setTestVar] = useState("");
  const [testValue, setTestValue] = useState(0);
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleRun = async () => {
    if (!sessionId || !testVar) { toast.error("Select a variable"); return; }
    setLoading(true);
    try {
      const result = await testsApi.oneSampleTTest({ session_id: sessionId, variable: testVar, test_value: testValue });
      addOutputBlock({
        id: crypto.randomUUID(),
        type: "table",
        title: `One-Sample T Test — ${testVar} (μ₀ = ${testValue})`,
        content: result,
        created_at: new Date(),
        procedure: "ttest-onesample",
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
        <h3 className="font-bold text-sm mb-3">One-Sample T Test</h3>
        <div className="mb-2">
          <label className="text-xs text-gray-600 block mb-1">Test variable:</label>
          <select className="w-full border border-gray-300 rounded px-2 py-1 text-sm" value={testVar} onChange={(e) => setTestVar(e.target.value)}>
            <option value="">-- Select --</option>
            {metadata?.variables.filter((v) => v.var_type === "numeric").map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
          </select>
        </div>
        <div className="mb-4">
          <label className="text-xs text-gray-600 block mb-1">Test value (H₀: μ =):</label>
          <input
            type="number"
            className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
            value={testValue}
            onChange={(e) => setTestValue(Number(e.target.value))}
          />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50">Cancel</button>
          <button onClick={handleRun} disabled={loading} className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">{loading ? "Running..." : "OK"}</button>
        </div>
      </div>
    </div>
  );
}
