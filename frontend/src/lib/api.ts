import axios, { AxiosInstance, AxiosError } from "axios";
import type { DatasetMeta, DatasetSession, DataPage, JobStatus } from "@/types/dataset";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// Response interceptor — handle session expiry and extract error messages
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status;
    const data = error.response?.data as Record<string, unknown> | undefined;

    // Detect session-not-found → clear stale session
    if (status === 404 && data?.error === "SESSION_NOT_FOUND") {
      // Dynamically import to avoid circular deps
      import("@/stores/datasetStore").then(({ useDatasetStore }) => {
        useDatasetStore.getState().clearSession();
      });
      return Promise.reject(
        new Error("Session expired. The server was restarted. Please re-upload your data file.")
      );
    }

    // Extract the most useful error message
    let message = "An unexpected error occurred";
    if (data) {
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (typeof data.detail === "object" && data.detail !== null) {
        const detail = data.detail as Record<string, string>;
        message = detail.message || detail.msg || JSON.stringify(data.detail);
      } else if (typeof data.message === "string") {
        message = data.message;
      }
    } else if (error.message) {
      message = error.message;
    }

    // Add status context for common errors
    if (status === 503) {
      message = "Server is temporarily unavailable (cold start). Please try again in a few seconds.";
    } else if (status === 422 && !data?.detail) {
      message = "Invalid request. Please check your input parameters.";
    }

    return Promise.reject(new Error(message));
  }
);

// ── Files ─────────────────────────────────────────────
export const filesApi = {
  upload: async (file: File): Promise<DatasetSession> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<DatasetSession>("/files/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },

  getData: async (sessionId: string, page = 1, pageSize = 100): Promise<DataPage> => {
    const res = await apiClient.get<DataPage>(`/files/${sessionId}/data`, {
      params: { page, page_size: pageSize },
    });
    return res.data;
  },

  getMeta: async (sessionId: string): Promise<DatasetMeta> => {
    const res = await apiClient.get<DatasetMeta>(`/files/${sessionId}/meta`);
    return res.data;
  },

  updateMeta: async (sessionId: string, meta: Partial<DatasetMeta>): Promise<DatasetMeta> => {
    const res = await apiClient.put<DatasetMeta>(`/files/${sessionId}/meta`, meta);
    return res.data;
  },

  exportSav: async (sessionId: string): Promise<Blob> => {
    const res = await apiClient.post(`/files/${sessionId}/export/sav`, {}, { responseType: "blob" });
    return res.data;
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/files/${sessionId}`);
  },
};

// ── Descriptives ─────────────────────────────────────
export const descriptivesApi = {
  frequencies: async (sessionId: string, variable: string, opts?: Record<string, unknown>) => {
    const res = await apiClient.post("/descriptives/frequencies", { session_id: sessionId, variable, ...opts });
    return res.data;
  },

  descriptives: async (sessionId: string, variables: string[]) => {
    const res = await apiClient.post("/descriptives/descriptives", { session_id: sessionId, variables });
    return res.data;
  },

  crosstabs: async (sessionId: string, rowVar: string, colVar: string) => {
    const res = await apiClient.post("/descriptives/crosstabs", { session_id: sessionId, row_var: rowVar, col_var: colVar });
    return res.data;
  },

  explore: async (sessionId: string, variable: string) => {
    const res = await apiClient.post("/descriptives/explore", { session_id: sessionId, variable });
    return res.data;
  },
};

// ── Tests ─────────────────────────────────────────────
export const testsApi = {
  independentTTest: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/tests/ttest/independent", payload);
    return res.data;
  },

  pairedTTest: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/tests/ttest/paired", payload);
    return res.data;
  },

  oneSampleTTest: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/tests/ttest/one-sample", payload);
    return res.data;
  },

  oneWayAnova: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/tests/anova/one-way", payload);
    return res.data;
  },

  means: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/tests/means", payload);
    return res.data;
  },
};

// ── Regression ────────────────────────────────────────
export const regressionApi = {
  correlation: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/regression/correlation", payload);
    return res.data;
  },

  linear: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/regression/linear", payload);
    return res.data;
  },

  logisticBinary: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/regression/logistic/binary", payload);
    return res.data;
  },
};

// ── Factor & Reliability ──────────────────────────────
export const factorApi = {
  efa: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/factor/efa", payload);
    return res.data;
  },

  efaStatus: async (jobId: string): Promise<JobStatus> => {
    const res = await apiClient.get<JobStatus>(`/factor/efa/${jobId}`);
    return res.data;
  },

  reliability: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post("/factor/reliability", payload);
    return res.data;
  },
};

// ── Transform ─────────────────────────────────────────
export const transformApi = {
  recode: async (sessionId: string, payload: Record<string, unknown>) => {
    const res = await apiClient.post(`/transform/${sessionId}/recode`, payload);
    return res.data;
  },

  compute: async (sessionId: string, payload: Record<string, unknown>) => {
    const res = await apiClient.post(`/transform/${sessionId}/compute`, payload);
    return res.data;
  },

  filter: async (sessionId: string, payload: Record<string, unknown>) => {
    const res = await apiClient.post(`/transform/${sessionId}/filter`, payload);
    return res.data;
  },

  sort: async (sessionId: string, payload: Record<string, unknown>) => {
    const res = await apiClient.post(`/transform/${sessionId}/sort`, payload);
    return res.data;
  },
};

// ── Jobs ──────────────────────────────────────────────
export const jobsApi = {
  getStatus: async (jobId: string): Promise<JobStatus> => {
    const res = await apiClient.get<JobStatus>(`/jobs/${jobId}`);
    return res.data;
  },
};

// ── Export ────────────────────────────────────────────
export const exportApi = {
  pdf: async (payload: Record<string, unknown>): Promise<Blob> => {
    const res = await apiClient.post("/export/pdf", payload, { responseType: "blob" });
    return res.data;
  },

  excel: async (payload: Record<string, unknown>): Promise<Blob> => {
    const res = await apiClient.post("/export/excel", payload, { responseType: "blob" });
    return res.data;
  },
};

// ── Health ────────────────────────────────────────────
export const healthApi = {
  check: async () => {
    const res = await apiClient.get("/health");
    return res.data;
  },
};
