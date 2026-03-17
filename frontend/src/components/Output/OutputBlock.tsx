"use client";

import { type ReactNode, useState } from "react";
import { useDatasetStore } from "@/stores/datasetStore";
import { formatNumber, significanceStars } from "@/lib/utils";
import type { OutputBlock as OutputBlockType } from "@/types/dataset";
import { X, ChevronDown, ChevronUp } from "lucide-react";

// Chart components (dynamically imported via next/dynamic inside each)
import { BoxPlot } from "@/components/Charts/BoxPlot";
import { Histogram } from "@/components/Charts/Histogram";
import { QQPlot } from "@/components/Charts/QQPlot";
import { ScatterPlot } from "@/components/Charts/ScatterPlot";
import { ScreePlot } from "@/components/Charts/ScreePlot";

interface Props {
  block: OutputBlockType;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function rv(value: unknown): string {
  if (value === null || value === undefined) return ".";
  if (typeof value === "number") return isNaN(value) ? "." : formatNumber(value);
  return String(value);
}

/** Generic SPSS-style pivot table from headers[] + rows[][] */
function PivotTable({
  headers,
  rows,
  firstColLeft = true,
}: {
  headers: string[];
  rows: unknown[][];
  firstColLeft?: boolean;
}) {
  if (!Array.isArray(headers) || !Array.isArray(rows) || !headers.length || !rows.length)
    return <p className="text-xs text-gray-400">No data</p>;
  return (
    <table className="spss-table">
      <thead>
        <tr>
          {headers.map((h, i) => <th key={i}>{h}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {(Array.isArray(row) ? row : Object.values(row as Record<string, unknown>)).map((cell, j) => (
              <td key={j} className={firstColLeft && j === 0 ? "text-left" : ""}>
                {rv(cell)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Section heading */
function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h4 className="text-[11px] font-bold text-gray-700 mt-3 mb-1 border-b border-gray-200 pb-0.5">
      {children}
    </h4>
  );
}

/** Simple key-value stat row list */
function StatRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex gap-2 text-xs">
      <span className="text-gray-500 min-w-[160px]">{label}</span>
      <span className="font-mono">{rv(value)}</span>
    </div>
  );
}

// ── Renderers by procedure ─────────────────────────────────────────────────────

function renderFrequencies(c: Record<string, unknown>): ReactNode {
  const headers = Array.isArray(c.headers) ? c.headers as string[] : [];
  // Support both array-of-arrays (new format) and array-of-dicts (legacy)
  let rows = Array.isArray(c.rows) ? c.rows as unknown[][] : [];
  if (rows.length > 0 && typeof rows[0] === "object" && !Array.isArray(rows[0])) {
    // Convert dict rows to array rows
    const dictRows = rows as unknown as Record<string, unknown>[];
    rows = dictRows.map(r => [r.value, r.label, r.count, r.percent, r.valid_percent, r.cumulative_percent]);
  }
  // Extract numeric values for histogram from row_details or rows
  const rowDetails = c.row_details as Record<string, unknown>[] | undefined;
  const numericValues: number[] = [];
  if (rowDetails) {
    for (const r of rowDetails) {
      const val = r.value;
      const count = r.count as number;
      if (typeof val === "number" && count > 0) {
        for (let i = 0; i < count; i++) numericValues.push(val);
      }
    }
  }
  return (
    <div>
      <div className="flex gap-4 text-xs text-gray-600 mb-2">
        <span>N Valid: <strong>{String(c.n_valid)}</strong></span>
        <span>Missing: <strong>{String(c.n_missing)}</strong></span>
        {c.mode !== null && c.mode !== undefined && (
          <span>Mode: <strong>{rv(c.mode)}</strong></span>
        )}
      </div>
      <PivotTable headers={headers} rows={rows} />
      {numericValues.length > 0 && (
        <div className="mt-3">
          <Histogram data={numericValues} title={`Frequency — ${rv(c.variable)}`} />
        </div>
      )}
    </div>
  );
}

function renderDescriptives(c: Record<string, unknown>): ReactNode {
  const headers = Array.isArray(c.headers) ? c.headers as string[] : [];
  const rows = Array.isArray(c.rows) ? c.rows as unknown[][] : [];
  return <PivotTable headers={headers} rows={rows} />;
}

function renderCrosstabs(c: Record<string, unknown>): ReactNode {
  const headers = Array.isArray(c.headers) ? c.headers as string[] : [];
  const rows = Array.isArray(c.rows) ? c.rows as unknown[][] : [];
  return (
    <div className="space-y-2">
      <PivotTable headers={headers} rows={rows} />
      <div className="flex flex-wrap gap-4 text-xs mt-2 text-gray-600">
        {c.chi2 !== null && c.chi2 !== undefined && (
          <StatRow label="Pearson Chi-Square" value={c.chi2} />
        )}
        {c.p_value !== null && c.p_value !== undefined && (
          <StatRow label="Asymptotic Sig. (2-sided)" value={c.p_value} />
        )}
        {c.cramers_v !== null && c.cramers_v !== undefined && (
          <StatRow label="Cramér's V" value={c.cramers_v} />
        )}
        {c.phi !== null && c.phi !== undefined && (
          <StatRow label="Phi" value={c.phi} />
        )}
        {c.fisher_exact_p !== null && c.fisher_exact_p !== undefined && (
          <StatRow label="Fisher's Exact Test (2-sided)" value={c.fisher_exact_p} />
        )}
        <StatRow label="N" value={c.n} />
      </div>
    </div>
  );
}

function renderExplore(c: Record<string, unknown>): ReactNode {
  const boxplotStats = c.boxplot_stats as Record<string, unknown> | null;
  const percentiles = c.percentiles as Record<string, number> | null;
  return (
    <div className="space-y-2">
      <SectionTitle>Normality Test — Shapiro-Wilk</SectionTitle>
      <table className="spss-table">
        <thead><tr><th>Statistic</th><th>N Valid</th><th>Sig.</th></tr></thead>
        <tbody>
          <tr>
            <td>{rv(c.shapiro_w)}</td>
            <td>{rv(c.n_valid)}</td>
            <td>{rv(c.shapiro_p)}</td>
          </tr>
        </tbody>
      </table>

      {percentiles && (
        <>
          <SectionTitle>Percentiles</SectionTitle>
          <table className="spss-table">
            <thead>
              <tr>
                {Object.keys(percentiles).map((k) => <th key={k}>P{k}</th>)}
              </tr>
            </thead>
            <tbody>
              <tr>
                {Object.values(percentiles).map((v, i) => <td key={i}>{rv(v)}</td>)}
              </tr>
            </tbody>
          </table>
        </>
      )}

      {boxplotStats && (
        <>
          <SectionTitle>Box Plot Statistics</SectionTitle>
          <div className="grid grid-cols-2 gap-x-8 gap-y-0.5">
            {["q1", "median", "q3", "whisker_low", "whisker_high"].map((k) =>
              boxplotStats[k] !== undefined ? (
                <StatRow key={k} label={k.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())} value={boxplotStats[k]} />
              ) : null
            )}
          </div>
          {/* Render Box Plot chart */}
          <div className="mt-3">
            <BoxPlot
              data={{
                q1: boxplotStats.q1 as number,
                median: boxplotStats.median as number,
                q3: boxplotStats.q3 as number,
                whisker_low: boxplotStats.whisker_low as number,
                whisker_high: boxplotStats.whisker_high as number,
                mild_outliers: (boxplotStats.mild_outliers as number[]) || [],
                extreme_outliers: (boxplotStats.extreme_outliers as number[]) || [],
              }}
              title={`Box Plot — ${rv(c.variable)}`}
            />
          </div>
        </>
      )}
    </div>
  );
}

function renderTTestIndependent(c: Record<string, unknown>): ReactNode {
  const groupStats = c.group_stats as Record<string, unknown>[] | null;
  return (
    <div className="space-y-3">
      {groupStats && groupStats.length > 0 && (
        <>
          <SectionTitle>Group Statistics</SectionTitle>
          <table className="spss-table">
            <thead><tr><th>Group</th><th>N</th><th>Mean</th><th>Std Dev</th><th>SE Mean</th></tr></thead>
            <tbody>
              {groupStats.map((g, i) => (
                <tr key={i}>
                  <td className="text-left">{rv(g.group)}</td>
                  <td>{rv(g.n)}</td>
                  <td>{rv(g.mean)}</td>
                  <td>{rv(g.std)}</td>
                  <td>{rv(g.se)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <SectionTitle>Independent Samples Test</SectionTitle>
      <table className="spss-table">
        <thead>
          <tr>
            <th>Assumption</th>
            <th>Levene F</th>
            <th>Levene p</th>
            <th>t</th>
            <th>df</th>
            <th>Sig. (2-tailed)</th>
            <th>Mean Diff.</th>
            <th>95% CI Lower</th>
            <th>95% CI Upper</th>
            <th>Cohen's d</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="text-left text-[10px]">
              {c.equal_var ? "Equal variances assumed" : "Equal variances not assumed"}
            </td>
            <td>{rv(c.levene_F)}</td>
            <td>{rv(c.levene_p)}</td>
            <td>{rv(c.statistic)}</td>
            <td>{rv(c.df)}</td>
            <td>{rv(c.pvalue)}</td>
            <td>{rv(c.mean_diff)}</td>
            <td>{rv(c.ci_lower)}</td>
            <td>{rv(c.ci_upper)}</td>
            <td>{rv(c.cohen_d)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function renderTTestPaired(c: Record<string, unknown>): ReactNode {
  return (
    <div className="space-y-3">
      <SectionTitle>Paired Differences</SectionTitle>
      <table className="spss-table">
        <thead>
          <tr>
            <th>Pair</th><th>N</th><th>Mean Diff.</th><th>Std Dev</th><th>SE Mean</th>
            <th>t</th><th>df</th><th>Sig.</th><th>95% CI Lower</th><th>95% CI Upper</th><th>Cohen's dz</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="text-left text-[10px]">{rv(c.var1)} – {rv(c.var2)}</td>
            <td>{rv(c.n)}</td>
            <td>{rv(c.mean_diff)}</td>
            <td>{rv(c.std_diff)}</td>
            <td>{rv(c.se_diff)}</td>
            <td>{rv(c.statistic)}</td>
            <td>{rv(c.df)}</td>
            <td>{rv(c.pvalue)}</td>
            <td>{rv(c.ci_lower)}</td>
            <td>{rv(c.ci_upper)}</td>
            <td>{rv(c.cohen_dz)}</td>
          </tr>
        </tbody>
      </table>
      <div className="text-xs text-gray-500 mt-1">
        Correlation between vars: r = {rv(c.correlation)}, p = {rv(c.correlation_p)}
      </div>
    </div>
  );
}

function renderTTestOneSample(c: Record<string, unknown>): ReactNode {
  return (
    <div className="space-y-3">
      <SectionTitle>One-Sample Statistics</SectionTitle>
      <table className="spss-table">
        <thead><tr><th>Variable</th><th>N</th><th>Mean</th><th>Std Dev</th><th>SE Mean</th></tr></thead>
        <tbody>
          <tr>
            <td className="text-left">{rv(c.variable)}</td>
            <td>{rv(c.n)}</td>
            <td>{rv(c.mean)}</td>
            <td>{rv(c.std)}</td>
            <td>{rv(c.se)}</td>
          </tr>
        </tbody>
      </table>

      <SectionTitle>One-Sample Test (Test Value = {rv(c.test_value)})</SectionTitle>
      <table className="spss-table">
        <thead>
          <tr>
            <th>Variable</th><th>t</th><th>df</th><th>Sig. (2-tailed)</th>
            <th>Mean Diff.</th><th>95% CI Lower</th><th>95% CI Upper</th><th>Cohen's d</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="text-left">{rv(c.variable)}</td>
            <td>{rv(c.statistic)}</td>
            <td>{rv(c.df)}</td>
            <td>{rv(c.pvalue)}</td>
            <td>{rv(c.mean_diff)}</td>
            <td>{rv(c.ci_lower)}</td>
            <td>{rv(c.ci_upper)}</td>
            <td>{rv(c.cohen_d)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function renderAnovaOneWay(c: Record<string, unknown>): ReactNode {
  const groupStats = c.group_stats as Record<string, unknown>[] | null;
  const posthoc = c.posthoc_results as Record<string, unknown>[] | null;
  const anovaTable = c.anova_table as { headers: string[]; rows: unknown[][] } | null;
  return (
    <div className="space-y-3">
      {groupStats && groupStats.length > 0 && (
        <>
          <SectionTitle>Descriptives</SectionTitle>
          <table className="spss-table">
            <thead><tr><th>Group</th><th>N</th><th>Mean</th><th>Std Dev</th><th>SE Mean</th></tr></thead>
            <tbody>
              {groupStats.map((g, i) => (
                <tr key={i}>
                  <td className="text-left">{rv(g.group)}</td>
                  <td>{rv(g.n)}</td>
                  <td>{rv(g.mean)}</td>
                  <td>{rv(g.std)}</td>
                  <td>{rv(g.se)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {anovaTable && (
        <>
          <SectionTitle>ANOVA</SectionTitle>
          <PivotTable headers={anovaTable.headers} rows={anovaTable.rows} />
        </>
      )}

      <div className="text-xs text-gray-600 flex gap-4">
        <StatRow label="η² (Eta squared)" value={c.eta_squared} />
        <StatRow label="Levene's F" value={c.levene_F} />
        <StatRow label="Levene's p" value={c.levene_p} />
      </div>

      {posthoc && posthoc.length > 0 && (
        <>
          <SectionTitle>Post-Hoc Comparisons</SectionTitle>
          <table className="spss-table">
            <thead>
              <tr>
                <th>Group 1</th><th>Group 2</th><th>Mean Diff.</th>
                {posthoc[0].p_value !== undefined && <th>p</th>}
                {posthoc[0].ci_lower !== undefined && <th>95% CI Lower</th>}
                {posthoc[0].ci_upper !== undefined && <th>95% CI Upper</th>}
                {posthoc[0].se !== undefined && <th>SE</th>}
                <th>Sig.</th>
              </tr>
            </thead>
            <tbody>
              {posthoc.map((row, i) => (
                <tr key={i}>
                  <td className="text-left">{rv(row.group_1)}</td>
                  <td className="text-left">{rv(row.group_2)}</td>
                  <td>{rv(row.mean_diff)}</td>
                  {row.p_value !== undefined && <td>{rv(row.p_value)}</td>}
                  {row.ci_lower !== undefined && <td>{rv(row.ci_lower)}</td>}
                  {row.ci_upper !== undefined && <td>{rv(row.ci_upper)}</td>}
                  {row.se !== undefined && <td>{rv(row.se)}</td>}
                  <td>{row.reject !== undefined ? (row.reject ? "Yes*" : "No") : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function renderMeans(c: Record<string, unknown>): ReactNode {
  const groupMeans = c.group_means as Record<string, unknown>[] | null;
  return (
    <div>
      <SectionTitle>Report — {rv(c.dep_var)} by {rv(c.factor_var)}</SectionTitle>
      {groupMeans && groupMeans.length > 0 && (
        <table className="spss-table">
          <thead>
            <tr><th>{rv(c.factor_var)}</th><th>N</th><th>Mean</th><th>Std Dev</th><th>SE Mean</th><th>Min</th><th>Max</th></tr>
          </thead>
          <tbody>
            {groupMeans.map((g, i) => (
              <tr key={i} className={rv(g.group) === "Total" ? "font-semibold bg-gray-50" : ""}>
                <td className="text-left">{rv(g.group)}</td>
                <td>{rv(g.n)}</td>
                <td>{rv(g.mean)}</td>
                <td>{rv(g.std)}</td>
                <td>{rv(g.se)}</td>
                <td>{rv(g.min)}</td>
                <td>{rv(g.max)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function renderCorrelation(c: Record<string, unknown>): ReactNode {
  const variables = c.variables as string[];
  const rMatrix = c.r_matrix as (number | null)[][];
  const pMatrix = c.p_matrix as (number | null)[][];
  const nMatrix = c.n_matrix as number[][];
  if (!variables || !rMatrix) {
    const fallbackH = Array.isArray(c.headers) ? c.headers as string[] : [];
    const fallbackR = Array.isArray(c.rows) ? c.rows as unknown[][] : [];
    return <PivotTable headers={fallbackH} rows={fallbackR} />;
  }

  return (
    <div>
      <SectionTitle>Correlations ({rv(c.method)})</SectionTitle>
      <table className="spss-table">
        <thead>
          <tr>
            <th></th>
            {variables.map((v) => <th key={v}>{v}</th>)}
          </tr>
        </thead>
        <tbody>
          {variables.map((rowVar, i) => (
            <>
              <tr key={`r-${i}`}>
                <td className="text-left text-[10px] pr-4">
                  <strong>{rowVar}</strong><br />r
                </td>
                {variables.map((_, j) => {
                  const r = rMatrix[i][j];
                  const p = pMatrix[i][j];
                  const stars = p !== null && p !== undefined ? significanceStars(p) : "";
                  return (
                    <td key={j}>
                      {r === null ? "—" : formatNumber(r)}
                      {stars && <sup className="text-red-600">{stars}</sup>}
                    </td>
                  );
                })}
              </tr>
              <tr key={`p-${i}`} className="text-[10px] text-gray-500">
                <td className="text-left text-[10px] pl-4">Sig. (2-tailed)</td>
                {variables.map((_, j) => (
                  <td key={j}>{pMatrix[i][j] !== null && pMatrix[i][j] !== undefined ? rv(pMatrix[i][j]) : ""}</td>
                ))}
              </tr>
              <tr key={`n-${i}`} className="text-[10px] text-gray-400">
                <td className="text-left text-[10px] pl-4">N</td>
                {variables.map((_, j) => (
                  <td key={j}>{nMatrix?.[i]?.[j] ?? ""}</td>
                ))}
              </tr>
            </>
          ))}
        </tbody>
      </table>
      <p className="text-[9px] text-gray-400 mt-1">**. p &lt; .01 (2-tailed) &nbsp; *. p &lt; .05 (2-tailed)</p>
    </div>
  );
}

function renderLinearRegression(c: Record<string, unknown>): ReactNode {
  const anovaTable = c.anova_table as { headers: string[]; rows: unknown[][] } | null;
  const coefficients = c.coefficients as Record<string, unknown>[] | null;
  const residualsData = c.residuals_data as Record<string, unknown> | null;
  return (
    <div className="space-y-3">
      <SectionTitle>Model Summary</SectionTitle>
      <table className="spss-table">
        <thead>
          <tr><th>R</th><th>R²</th><th>Adj. R²</th><th>Std. Error</th><th>Durbin-Watson</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>{rv(c.r)}</td>
            <td>{rv(c.r2)}</td>
            <td>{rv(c.adj_r2)}</td>
            <td>{rv(c.std_error_estimate)}</td>
            <td>{rv(c.durbin_watson)}</td>
          </tr>
        </tbody>
      </table>

      {anovaTable && (
        <>
          <SectionTitle>ANOVA</SectionTitle>
          <PivotTable headers={anovaTable.headers} rows={anovaTable.rows} />
          <div className="text-xs text-gray-500">
            F({rv(c.f_df1)}, {rv(c.f_df2)}) = {rv(c.f_stat)}, p = {rv(c.f_pvalue)}
          </div>
        </>
      )}

      {coefficients && (
        <>
          <SectionTitle>Coefficients</SectionTitle>
          <table className="spss-table">
            <thead>
              <tr>
                <th>Variable</th><th>B</th><th>Std Error</th><th>β (Beta)</th>
                <th>t</th><th>Sig.</th><th>95% CI Lower</th><th>95% CI Upper</th>
                <th>VIF</th><th>Tolerance</th>
              </tr>
            </thead>
            <tbody>
              {coefficients.map((coef, i) => (
                <tr key={i}>
                  <td className="text-left">{rv(coef.variable)}</td>
                  <td>{rv(coef.B)}</td>
                  <td>{rv(coef.std_error)}</td>
                  <td>{rv(coef.beta)}</td>
                  <td>{rv(coef.t)}</td>
                  <td>{rv(coef.pvalue)}</td>
                  <td>{rv(coef.ci_lower)}</td>
                  <td>{rv(coef.ci_upper)}</td>
                  <td>{rv(coef.vif)}</td>
                  <td>{rv(coef.tolerance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* Residual Scatter Plot */}
      {residualsData && (
        <>
          <SectionTitle>Standardized Residuals vs. Predicted</SectionTitle>
          <ScatterPlot
            x={(residualsData.leverage as number[]) || []}
            y={(residualsData.standardized_residuals as number[]) || []}
            xLabel="Leverage"
            yLabel="Standardized Residuals"
          />
        </>
      )}
    </div>
  );
}

function renderLogisticRegression(c: Record<string, unknown>): ReactNode {
  const coefficients = c.coefficients as Record<string, unknown>[] | null;
  const classTable = c.classification_table as Record<string, unknown> | null;
  return (
    <div className="space-y-3">
      <SectionTitle>Omnibus Tests — Model Summary</SectionTitle>
      <table className="spss-table">
        <thead><tr><th>-2 Log likelihood</th><th>Cox &amp; Snell R²</th><th>Nagelkerke R²</th></tr></thead>
        <tbody>
          <tr>
            <td>{rv(c.neg_2LL)}</td>
            <td>{rv(c.cox_snell_r2)}</td>
            <td>{rv(c.nagelkerke_r2)}</td>
          </tr>
        </tbody>
      </table>

      {c.hosmer_lemeshow_chi2 !== null && c.hosmer_lemeshow_chi2 !== undefined && (
        <div className="text-xs text-gray-600">
          Hosmer-Lemeshow: χ² = {rv(c.hosmer_lemeshow_chi2)}, p = {rv(c.hosmer_lemeshow_p)}
        </div>
      )}

      {coefficients && (
        <>
          <SectionTitle>Variables in the Equation</SectionTitle>
          <table className="spss-table">
            <thead>
              <tr>
                <th>Variable</th><th>B</th><th>Std Error</th><th>Wald</th>
                <th>df</th><th>Sig.</th><th>Exp(B)</th><th>95% CI Lower</th><th>95% CI Upper</th>
              </tr>
            </thead>
            <tbody>
              {coefficients.map((coef, i) => (
                <tr key={i}>
                  <td className="text-left">{rv(coef.variable)}</td>
                  <td>{rv(coef.B)}</td>
                  <td>{rv(coef.std_error)}</td>
                  <td>{rv(coef.wald)}</td>
                  <td>{rv(coef.df)}</td>
                  <td>{rv(coef.pvalue)}</td>
                  <td className="font-semibold">{rv(coef.exp_B)}</td>
                  <td>{rv(coef.ci_lower)}</td>
                  <td>{rv(coef.ci_upper)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {classTable && (
        <>
          <SectionTitle>Classification Table</SectionTitle>
          <table className="spss-table">
            <thead><tr><th>TP</th><th>TN</th><th>FP</th><th>FN</th><th>Overall Accuracy %</th></tr></thead>
            <tbody>
              <tr>
                <td>{rv(classTable.tp)}</td>
                <td>{rv(classTable.tn)}</td>
                <td>{rv(classTable.fp)}</td>
                <td>{rv(classTable.fn)}</td>
                <td className="font-semibold">{rv(classTable.accuracy_pct)}%</td>
              </tr>
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function renderEFA(c: Record<string, unknown>): ReactNode {
  const headers = Array.isArray(c.headers) ? c.headers as string[] : [];
  const rows = Array.isArray(c.rows) ? c.rows as unknown[][] : [];
  const variables = c.variables as string[];
  const eigenvalues = c.eigenvalues as number[] | null;
  return (
    <div className="space-y-3">
      <SectionTitle>KMO and Bartlett's Test</SectionTitle>
      <table className="spss-table">
        <tbody>
          <tr>
            <td className="text-left">Kaiser-Meyer-Olkin MSA</td>
            <td className="font-semibold">{rv(c.kmo)}</td>
          </tr>
          {c.bartlett_chi2 !== null && (
            <>
              <tr>
                <td className="text-left">Bartlett's χ²</td>
                <td>{rv(c.bartlett_chi2)}</td>
              </tr>
              <tr>
                <td className="text-left">df</td>
                <td>{rv(c.bartlett_df)}</td>
              </tr>
              <tr>
                <td className="text-left">Sig.</td>
                <td>{rv(c.bartlett_p)}</td>
              </tr>
            </>
          )}
        </tbody>
      </table>

      <SectionTitle>Total Variance Explained</SectionTitle>
      <table className="spss-table">
        <thead>
          <tr>
            <th>Factor</th><th>Eigenvalue</th><th>% of Variance</th><th>Cumulative %</th>
          </tr>
        </thead>
        <tbody>
          {(eigenvalues ?? []).map((ev, i) => (
            <tr key={i}>
              <td>Factor {i + 1}</td>
              <td>{rv(ev)}</td>
              <td>{rv((c.explained_variance as number[])[i])}</td>
              <td>{rv((c.cumulative_variance as number[])[i])}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Scree Plot chart */}
      {eigenvalues && eigenvalues.length > 0 && (
        <div className="mt-3">
          <ScreePlot eigenvalues={eigenvalues} />
        </div>
      )}

      {headers && rows && (
        <>
          <SectionTitle>
            {c.rotation !== "none" ? `Rotated Component Matrix (${rv(c.rotation)})` : "Component Matrix"}
          </SectionTitle>
          <PivotTable headers={headers} rows={rows} />
        </>
      )}

      <div className="text-xs text-gray-500">
        Extraction: {rv(c.extraction)} | Rotation: {rv(c.rotation)} | N = {rv(c.n_cases)}
      </div>
    </div>
  );
}

function renderReliability(c: Record<string, unknown>): ReactNode {
  const itemStats = c.item_stats as Record<string, unknown>[] | null;
  return (
    <div className="space-y-3">
      <SectionTitle>Reliability Statistics</SectionTitle>
      <table className="spss-table">
        <thead><tr><th>Cronbach's α</th><th>95% CI Lower</th><th>95% CI Upper</th><th>N Items</th><th>N Cases</th></tr></thead>
        <tbody>
          <tr>
            <td className="font-bold text-green-700">{rv(c.cronbach_alpha)}</td>
            <td>{rv(c.cronbach_alpha_ci_lower)}</td>
            <td>{rv(c.cronbach_alpha_ci_upper)}</td>
            <td>{rv(c.n_items)}</td>
            <td>{rv(c.n_cases)}</td>
          </tr>
        </tbody>
      </table>

      {itemStats && itemStats.length > 0 && (
        <>
          <SectionTitle>Item-Total Statistics</SectionTitle>
          <table className="spss-table">
            <thead>
              <tr>
                <th>Item</th><th>Mean</th><th>Std Dev</th>
                <th>Corrected Item-Total r</th><th>Cronbach's α if Deleted</th>
              </tr>
            </thead>
            <tbody>
              {itemStats.map((item, i) => (
                <tr key={i}>
                  <td className="text-left">{rv(item.variable)}</td>
                  <td>{rv(item.mean)}</td>
                  <td>{rv(item.std)}</td>
                  <td>{rv(item.item_total_corr)}</td>
                  <td>{rv(item.alpha_if_deleted)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

// ── AI Renderers ───────────────────────────────────────────────────────────────

function renderAIInsightCard(insight: Record<string, unknown>): ReactNode {
  return (
    <div className="bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200 rounded-lg p-4 space-y-3">
      {!!insight.headline && (
        <div className="flex items-start gap-2">
          <span className="text-lg">💡</span>
          <p className="text-sm font-semibold text-blue-900">{String(insight.headline)}</p>
        </div>
      )}
      {!!insight.interpretation && (
        <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">
          {String(insight.interpretation)}
        </p>
      )}
      {!!insight.significance && (
        <div className="flex items-start gap-2 bg-white/60 rounded p-2">
          <span className="text-sm">📊</span>
          <p className="text-xs text-gray-600">{String(insight.significance)}</p>
        </div>
      )}
      {Array.isArray(insight.recommendations) && insight.recommendations.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase mb-1">Recommendations</p>
          <ul className="list-disc list-inside text-xs text-gray-600 space-y-0.5">
            {(insight.recommendations as string[]).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Chart Renderer (SVG-based) ──────────────────────────────────────────────

function renderSVGChart(chart: Record<string, unknown>): ReactNode {
  const chartType = String(chart.chart_type || "bar");
  const title = String(chart.title || "");
  const xArr = Array.isArray(chart.x) ? chart.x : [];
  const yArr = Array.isArray(chart.y) ? (chart.y as number[]) : [];
  const xLabel = chart.x_label ? String(chart.x_label) : "";
  const yLabel = chart.y_label ? String(chart.y_label) : "";
  const refLine = typeof chart.reference_line === "number" ? chart.reference_line : null;

  if ((chartType === "bar" || chartType === "line" || chartType === "scatter") && xArr.length > 0 && yArr.length > 0) {
    const w = 500, h = 250, pad = { t: 20, r: 20, b: 50, l: 60 };
    const plotW = w - pad.l - pad.r;
    const plotH = h - pad.t - pad.b;
    const maxY = Math.max(...yArr, 0) * 1.15 || 1;
    const minY = Math.min(...yArr, 0);
    const rangeY = (maxY - minY) || 1;
    const barW = Math.max(8, Math.min(40, plotW / xArr.length - 4));
    const colors = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed", "#0891b2"];

    const toY = (v: number) => pad.t + plotH - ((v - minY) / rangeY) * plotH;
    const toX = (i: number) => pad.l + (i + 0.5) * (plotW / xArr.length);

    return (
      <div className="bg-white border border-gray-200 rounded-lg p-3">
        {title && <p className="text-xs font-semibold text-gray-700 mb-2">📈 {title}</p>}
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-h-[280px]" preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
            const gy = pad.t + plotH * (1 - pct);
            const val = minY + rangeY * pct;
            return (
              <g key={pct}>
                <line x1={pad.l} y1={gy} x2={w - pad.r} y2={gy} stroke="#e5e7eb" strokeWidth={0.5} />
                <text x={pad.l - 6} y={gy + 3} textAnchor="end" fill="#9ca3af" fontSize={9}>
                  {Number.isInteger(val) ? val : val.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* Reference line */}
          {refLine !== null && refLine >= minY && refLine <= maxY && (
            <line x1={pad.l} y1={toY(refLine)} x2={w - pad.r} y2={toY(refLine)}
              stroke="#ef4444" strokeWidth={1.5} strokeDasharray="6,3" />
          )}

          {/* Data */}
          {chartType === "bar" && yArr.map((v, i) => {
            const barH = ((v - Math.min(minY, 0)) / rangeY) * plotH;
            const baseY = toY(Math.max(0, minY));
            return (
              <rect key={i} x={toX(i) - barW / 2} y={v >= 0 ? baseY - barH : baseY}
                width={barW} height={Math.abs(barH)} rx={2}
                fill={colors[i % colors.length]} opacity={0.85} />
            );
          })}

          {chartType === "line" && (
            <polyline fill="none" stroke="#2563eb" strokeWidth={2}
              points={yArr.map((v, i) => `${toX(i)},${toY(v)}`).join(" ")} />
          )}
          {chartType === "line" && yArr.map((v, i) => (
            <circle key={i} cx={toX(i)} cy={toY(v)} r={3} fill="#2563eb" />
          ))}

          {chartType === "scatter" && yArr.map((v, i) => (
            <circle key={i} cx={toX(i)} cy={toY(v)} r={4} fill="#2563eb" opacity={0.7} />
          ))}

          {/* X labels */}
          {xArr.map((label, i) => (
            <text key={i} x={toX(i)} y={h - pad.b + 16} textAnchor="middle" fill="#6b7280" fontSize={8}
              transform={`rotate(-30, ${toX(i)}, ${h - pad.b + 16})`}>
              {String(label).length > 12 ? String(label).slice(0, 12) + "…" : String(label)}
            </text>
          ))}

          {/* Axis labels */}
          {xLabel && <text x={w / 2} y={h - 4} textAnchor="middle" fill="#6b7280" fontSize={10}>{xLabel}</text>}
          {yLabel && (
            <text x={14} y={h / 2} textAnchor="middle" fill="#6b7280" fontSize={10}
              transform={`rotate(-90, 14, ${h / 2})`}>{yLabel}</text>
          )}
        </svg>
      </div>
    );
  }

  // Heatmap
  if (chartType === "heatmap") {
    const xLabels = Array.isArray(chart.x_labels) ? chart.x_labels as string[] : [];
    const yLabels = Array.isArray(chart.y_labels) ? chart.y_labels as string[] : [];
    const z = Array.isArray(chart.z) ? chart.z as number[][] : [];
    if (!z.length) return null;

    return (
      <div className="bg-white border border-gray-200 rounded-lg p-3">
        {title && <p className="text-xs font-semibold text-gray-700 mb-2">📈 {title}</p>}
        <div className="overflow-auto">
          <table className="spss-table text-[10px]">
            <thead>
              <tr><th></th>{xLabels.map((l, i) => <th key={i}>{l}</th>)}</tr>
            </thead>
            <tbody>
              {z.map((row, ri) => (
                <tr key={ri}>
                  <td className="font-semibold bg-gray-50">{yLabels[ri] || ri}</td>
                  {row.map((val, ci) => {
                    const absVal = Math.abs(val || 0);
                    const color = val > 0
                      ? `rgba(37, 99, 235, ${absVal})` // blue for positive
                      : `rgba(220, 38, 38, ${absVal})`; // red for negative
                    return (
                      <td key={ci} style={{ backgroundColor: color, color: absVal > 0.5 ? "white" : "black" }}>
                        {typeof val === "number" ? val.toFixed(3) : String(val)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return null;
}

function renderAICharts(charts: unknown): ReactNode {
  if (!Array.isArray(charts) || charts.length === 0) return null;
  return (
    <div className="space-y-3">
      {(charts as Record<string, unknown>[]).map((chart, i) => (
        <div key={i}>{renderSVGChart(chart)}</div>
      ))}
    </div>
  );
}

// ── Table Renderer ──────────────────────────────────────────────────────

function renderAITables(tables: unknown): ReactNode {
  if (!Array.isArray(tables) || tables.length === 0) return null;
  return (
    <div className="space-y-3">
      {(tables as Record<string, unknown>[]).map((table, i) => {
        const title = String(table.title || "");
        const columns = Array.isArray(table.columns) ? table.columns as string[] : [];
        const rows = Array.isArray(table.rows) ? table.rows as unknown[][] : [];
        if (!columns.length && !rows.length) return null;
        return (
          <div key={i}>
            {title && (
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                📝 {title}
              </p>
            )}
            <PivotTable headers={columns} rows={rows} />
          </div>
        );
      })}
    </div>
  );
}

// ── AI Procedure Renderers ────────────────────────────────────────────────

function renderAIAnalyze(c: Record<string, unknown>): ReactNode {
  const insight = c.insight as Record<string, unknown> | undefined;
  const plan = c.plan as Record<string, unknown> | undefined;
  const charts = c.charts;
  const tables = c.tables;
  const meta = c.meta as Record<string, unknown> | undefined;
  const trace = c.decision_trace as Record<string, unknown> | undefined;

  const degraded = meta?.degraded === true;
  const confidence = typeof meta?.confidence === "number" ? meta.confidence : null;
  const requestedMethod = trace?.requested_method || meta?.original_method || plan?.method;
  const executedMethod = trace?.executed_method || meta?.analysis_type || plan?.method;
  const constraints = Array.isArray(trace?.statistical_constraints) ? trace.statistical_constraints as string[] : [];
  const nObs: number | null = typeof trace?.n_observations === "number" ? trace.n_observations : null;

  // Confidence badge color
  const confColor = confidence !== null
    ? confidence >= 0.7 ? "bg-green-100 text-green-800 border-green-300"
    : confidence >= 0.3 ? "bg-yellow-100 text-yellow-800 border-yellow-300"
    : "bg-red-100 text-red-800 border-red-300"
    : "";
  const confLabel = confidence !== null
    ? confidence >= 0.7 ? "High" : confidence >= 0.3 ? "Medium" : "Low"
    : "";

  const confBadge: ReactNode = confidence !== null ? (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${confColor}`}>
      📊 Confidence: {(confidence * 100).toFixed(0)}% ({confLabel})
    </span>
  ) : null;

  const nObsInfo: ReactNode = nObs !== null ? (
    <div className="text-[10px] text-gray-400">
      Data: {nObs} observation{nObs !== 1 ? "s" : ""}
      {!!plan?.description && <> — {String(plan.description)}</>}
    </div>
  ) : null;

  const fallbackReason: ReactNode = degraded && trace?.fallback_reason ? (
    <div className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 space-y-1">
      <div className="flex items-start gap-1.5">
        <span className="mt-0.5">⚡</span>
        <div>
          <strong>Why fallback?</strong> {String(trace.fallback_reason)}
        </div>
      </div>
    </div>
  ) : null;

  const constraintsList: ReactNode = constraints.length > 0 ? (
    <div className="text-[10px] text-gray-500 space-y-0.5">
      {constraints.map((item, i) => (
        <div key={i} className="flex items-start gap-1">
          <span className="text-red-400 mt-px">•</span>
          <span>{String(item)}</span>
        </div>
      ))}
    </div>
  ) : null;

  return (
    <div className="space-y-4">
      {/* Decision Trace Banner */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 text-xs">
            <span>🔬</span>
            <span className="text-gray-500">Requested:</span>
            <strong className="text-gray-800">{String(requestedMethod).replace(/_/g, " ")}</strong>
            {degraded && (
              <>
                <span className="text-gray-400">→</span>
                <span className="text-gray-500">Executed:</span>
                <strong className="text-blue-700">{String(executedMethod).replace(/_/g, " ")}</strong>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-amber-100 text-amber-800 border border-amber-300">
                  ↩ Fallback
                </span>
              </>
            )}
          </div>
          {confBadge}
        </div>
        {nObsInfo}
        {fallbackReason}
        {constraintsList}
      </div>

      {/* Insight */}
      {insight && renderAIInsightCard(insight)}

      {/* Charts + Tables */}
      {renderAICharts(charts)}
      {renderAITables(tables)}

      {/* Warnings */}
      {Array.isArray(plan?.warnings) && (plan.warnings as string[]).length > 0 && (
        <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
          ⚠️ {(plan.warnings as string[]).join("; ")}
        </div>
      )}
    </div>
  );
}

function renderAIAutoAnalysis(c: Record<string, unknown>): ReactNode {
  const analyses = Array.isArray(c.analyses) ? c.analyses as Record<string, unknown>[] : [];
  return (
    <div className="space-y-4">
      <div className="text-xs text-gray-500">
        {analyses.length} analyses completed
      </div>
      {analyses.map((item, i) => {
        const insight = item.insight as Record<string, unknown> | undefined;
        const hasError = !!item.error;
        return (
          <div key={i} className="border border-gray-200 rounded-lg overflow-hidden">
            <div className={`px-3 py-2 text-xs font-medium flex items-center gap-2 ${
              hasError ? "bg-red-50 text-red-800" : "bg-gray-100 text-gray-700"
            }`}>
              <span>{hasError ? "❌" : "✅"}</span>
              <span className="font-semibold">{String(item.method)}</span>
              <span className="text-gray-400">—</span>
              <span>{String(item.description)}</span>
            </div>
            <div className="p-3 space-y-3">
              {hasError ? (
                <p className="text-xs text-red-600">{String(item.error)}</p>
              ) : (
                <>
                  {insight && renderAIInsightCard(insight)}
                  {renderAICharts(item.charts)}
                  {renderAITables(item.tables)}
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function renderAIReport(c: Record<string, unknown>): ReactNode {
  const report = c.report as Record<string, unknown> | undefined;
  if (!report) return <p className="text-xs text-gray-400">No report data</p>;

  const sections = Array.isArray(report.sections) ? report.sections as Record<string, string>[] : [];
  return (
    <div className="space-y-4">
      {!!report.title && (
        <h3 className="text-base font-bold text-gray-800 border-b border-gray-300 pb-2">
          {String(report.title)}
        </h3>
      )}
      {sections.map((section, i) => (
        <div key={i}>
          <h4 className="text-sm font-semibold text-blue-900 mb-1">{section.heading}</h4>
          <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">{section.content}</p>
        </div>
      ))}
    </div>
  );
}

// ── Main router ────────────────────────────────────────────────────────────────

function renderContent(block: OutputBlockType): ReactNode {
  const content = block.content as Record<string, unknown>;
  if (!content) return <p className="text-xs text-gray-400">No content</p>;

  const procedure = block.procedure ?? "";

  if (procedure === "frequencies") return renderFrequencies(content);
  if (procedure === "descriptives") return renderDescriptives(content);
  if (procedure === "crosstabs") return renderCrosstabs(content);
  if (procedure === "explore") return renderExplore(content);
  if (procedure === "ttest-independent") return renderTTestIndependent(content);
  if (procedure === "ttest-paired") return renderTTestPaired(content);
  if (procedure === "ttest-onesample") return renderTTestOneSample(content);
  if (procedure === "anova-oneway") return renderAnovaOneWay(content);
  if (procedure === "means") return renderMeans(content);
  if (procedure === "correlation") return renderCorrelation(content);
  if (procedure === "linear_regression") return renderLinearRegression(content);
  if (procedure === "logistic") return renderLogisticRegression(content);
  if (procedure === "efa") return renderEFA(content);
  if (procedure === "reliability") return renderReliability(content);

  // AI procedures
  if (procedure === "ai-analyze") return renderAIAnalyze(content);
  if (procedure === "ai-auto-analyze") return renderAIAutoAnalysis(content);
  if (procedure === "ai-report") return renderAIReport(content);

  // Fallback: use generic headers/rows pivot table if present
  if (Array.isArray(content.headers) && Array.isArray(content.rows)) {
    return <PivotTable headers={content.headers as string[]} rows={content.rows as unknown[][]} />;
  }

  // Last resort fallback
  return (
    <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-60 font-mono">
      {JSON.stringify(content, null, 2)}
    </pre>
  );
}

// ── OutputBlock component ──────────────────────────────────────────────────────

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
          <p className="text-[10px] text-gray-300 mt-3 text-right select-none">
            {new Date(block.created_at).toLocaleTimeString()}
          </p>
        </div>
      )}
    </div>
  );
}
