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
  type: "table" | "chart";
  title: string;
  subtitle?: string;
  content: unknown;
  created_at: Date;
  procedure: string;
}
