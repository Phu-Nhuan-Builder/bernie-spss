"use client";

import { type ReactNode, useState } from "react";
import { useDatasetStore } from "@/stores/datasetStore";
import { formatNumber, significanceStars } from "@/lib/utils";
import type { OutputBlock as OutputBlockType } from "@/types/dataset";
import { X, ChevronDown, ChevronUp } from "lucide-react";

interface Props {
  block: OutputBlockType;
}

function renderValue(value: unknown): string {
  if (value === null || value === undefined) return ".";
  if (typeof value === "number") {
    if (isNaN(value)) return ".";
    return formatNumber(value);
  }
  return String(value);
}

function GenericTable({ data }: { data: Record<string, unknown>[] }) {
  if (!data || data.length === 0) return <p className="text-xs text-gray-400">No data</p>;
  const keys = Object.keys(data[0]);
  return (
    <table className="spss-table">
      <thead>
        <tr>
          {keys.map((k) => (
            <th key={k}>{k}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={i}>
            {keys.map((k) => (
              <td key={k}>{renderValue(row[k])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderContent(block: OutputBlockType): ReactNode {
  const content = block.content as Record<string, unknown>;
  if (!content) return <p className="text-xs text-gray-400">No content</p>;

  // Frequencies output
  if (block.procedure === "frequencies" && content.frequency_table) {
    const rows = content.frequency_table as Record<string, unknown>[];
    return <GenericTable data={rows} />;
  }

  // Descriptives output
  if (block.procedure === "descriptives" && content.statistics) {
    const rows = content.statistics as Record<string, unknown>[];
    return <GenericTable data={rows} />;
  }

  // Correlation output
  if (block.procedure === "correlation" && content.correlation_matrix) {
    const matrix = content.correlation_matrix as Record<string, Record<string, number>>;
    const vars = Object.keys(matrix);
    return (
      <table className="spss-table">
        <thead>
          <tr>
            <th></th>
            {vars.map((v) => <th key={v}>{v}</th>)}
          </tr>
        </thead>
        <tbody>
          {vars.map((rowVar) => (
            <tr key={rowVar}>
              <td className="font-semibold">{rowVar}</td>
              {vars.map((colVar) => {
                const val = matrix[rowVar]?.[colVar];
                const pval = (content.p_matrix as Record<string, Record<string, number>>)?.[rowVar]?.[colVar];
                const stars = pval !== undefined ? significanceStars(pval) : "";
                return (
                  <td key={colVar}>
                    {typeof val === "number" ? formatNumber(val) : "."}
                    {stars && <span className="text-red-600 text-[8pt]">{stars}</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  // Linear regression output
  if (block.procedure === "linear_regression") {
    return (
      <div className="space-y-4">
        {Boolean(content.model_summary) && (
          <div>
            <h4 className="text-xs font-semibold mb-1">Model Summary</h4>
            <GenericTable data={[content.model_summary as Record<string, unknown>]} />
          </div>
        )}
        {Boolean(content.anova) && (
          <div>
            <h4 className="text-xs font-semibold mb-1">ANOVA</h4>
            <GenericTable data={content.anova as Record<string, unknown>[]} />
          </div>
        )}
        {Boolean(content.coefficients) && (
          <div>
            <h4 className="text-xs font-semibold mb-1">Coefficients</h4>
            <GenericTable data={content.coefficients as Record<string, unknown>[]} />
          </div>
        )}
      </div>
    );
  }

  // T-test output
  if (block.procedure?.includes("ttest")) {
    return (
      <div className="space-y-4">
        {Boolean(content.group_stats) && (
          <div>
            <h4 className="text-xs font-semibold mb-1">Group Statistics</h4>
            <GenericTable data={content.group_stats as Record<string, unknown>[]} />
          </div>
        )}
        {Boolean(content.test_results) && (
          <div>
            <h4 className="text-xs font-semibold mb-1">Independent Samples Test</h4>
            <GenericTable data={content.test_results as Record<string, unknown>[]} />
          </div>
        )}
        {/* Fallback for one-sample / paired */}
        {!content.group_stats && !content.test_results && (
          <GenericTable data={Array.isArray(content) ? content : [content]} />
        )}
      </div>
    );
  }

  // Reliability
  if (block.procedure === "reliability") {
    return (
      <div className="space-y-4">
        {Boolean(content.scale_stats) && (
          <div>
            <h4 className="text-xs font-semibold mb-1">Scale Statistics</h4>
            <GenericTable data={[content.scale_stats as Record<string, unknown>]} />
          </div>
        )}
        {Boolean(content.item_stats) && (
          <div>
            <h4 className="text-xs font-semibold mb-1">Item-Total Statistics</h4>
            <GenericTable data={content.item_stats as Record<string, unknown>[]} />
          </div>
        )}
      </div>
    );
  }

  // Fallback: generic render
  if (Array.isArray(content)) {
    return <GenericTable data={content} />;
  }

  return (
    <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-60">
      {JSON.stringify(content, null, 2)}
    </pre>
  );
}

export function OutputBlock({ block }: Props) {
  const { removeOutputBlock } = useDatasetStore();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="bg-white border border-gray-300 rounded shadow-sm">
      {/* Block header */}
      <div className="flex items-center justify-between px-4 py-2 bg-spss-blue text-white rounded-t">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-2 text-left flex-1 min-w-0"
        >
          {collapsed ? (
            <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" />
          ) : (
            <ChevronUp className="w-3.5 h-3.5 flex-shrink-0" />
          )}
          <div className="min-w-0">
            <span className="text-xs font-semibold block truncate">{block.title}</span>
            {block.subtitle && (
              <span className="text-[10px] text-blue-200 block truncate">{block.subtitle}</span>
            )}
          </div>
        </button>
        <button
          onClick={() => removeOutputBlock(block.id)}
          className="ml-2 p-0.5 hover:bg-blue-700 rounded transition-colors flex-shrink-0"
          title="Remove block"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Block content */}
      {!collapsed && (
        <div className="p-4 overflow-auto max-h-[600px]">
          {renderContent(block)}
          <p className="text-[10px] text-gray-300 mt-2 text-right">
            {new Date(block.created_at).toLocaleTimeString()}
          </p>
        </div>
      )}
    </div>
  );
}
