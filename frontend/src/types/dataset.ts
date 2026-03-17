export type VariableMeasure = "nominal" | "ordinal" | "scale";
export type VariableType = "numeric" | "string" | "date";
export type VariableRole = "input" | "target" | "both" | "none" | "partition" | "split";

export interface ValueLabel {
  value: number | string;
  label: string;
}

export interface VariableMeta {
  name: string;
  label: string;
  var_type: VariableType;
  width: number;
  decimals: number;
  value_labels: Record<string, string>;
  missing_values: (number | string)[];
  measure: VariableMeasure;
  role: VariableRole;
}

export interface DatasetMeta {
  file_name: string;
  n_cases: number;
  n_vars: number;
  variables: VariableMeta[];
  encoding: string;
}

export interface DatasetSession {
  session_id: string;
  meta: DatasetMeta;
  created_at: string;
}

export type JobStatusEnum = "PENDING" | "PROGRESS" | "SUCCESS" | "FAILURE";

export interface JobStatus {
  job_id: string;
  status: JobStatusEnum;
  progress_msg?: string;
  result?: unknown;
  error?: string;
}

export interface DataPage {
  data: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
  n_vars: number;
}

export interface OutputBlock {
  id: string;
  type: "table" | "chart" | "ai-insight" | "ai-report";
  title: string;
  subtitle?: string;
  content: unknown;
  created_at: Date;
  procedure: string;
}

// ── AI Response Types ─────────────────────────────────
export interface AIInsight {
  headline: string;
  interpretation: string;
  significance: string;
  recommendations: string[];
}

export interface ChartSpec {
  chart_type: "bar" | "scatter" | "heatmap" | "boxplot" | "line";
  title: string;
  x?: (string | number)[];
  y?: number[];
  x_label?: string;
  y_label?: string;
  x_labels?: string[];
  y_labels?: string[];
  z?: number[][];
  error_y?: number[];
  data?: Record<string, unknown>;
  color_scale?: string;
  reference_line?: number;
}

export interface TableSpec {
  title: string;
  columns: string[];
  rows: unknown[][];
}

export interface AnalysisMeta {
  analysis_type: string;
  confidence: number;
}

export interface AIAnalysisItem {
  method: string;
  description: string;
  results?: Record<string, unknown>;
  insight?: AIInsight;
  charts?: ChartSpec[];
  tables?: TableSpec[];
  error?: string;
}

export interface AIAnalyzeResponse {
  status: string;
  intent?: Record<string, unknown>;
  plan?: Record<string, unknown>;
  results?: Record<string, unknown>;
  insight?: AIInsight;
  charts?: ChartSpec[];
  tables?: TableSpec[];
  meta?: AnalysisMeta;
  message?: string;
  dataset_schema?: Record<string, unknown>;
}

export interface AIAutoResponse {
  status: string;
  dataset_schema?: Record<string, unknown>;
  n_analyses: number;
  analyses: AIAnalysisItem[];
  message?: string;
}

export interface AIReportSection {
  heading: string;
  content: string;
}

export interface AIReportResponse {
  status: string;
  report?: {
    title: string;
    sections: AIReportSection[];
  };
  n_analyses: number;
  message?: string;
}

