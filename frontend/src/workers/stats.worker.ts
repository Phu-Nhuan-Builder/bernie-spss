/**
 * stats.worker.ts — Web Worker for client-side statistical previews
 *
 * Used for lightweight computations before sending to the server,
 * so the UI remains responsive during preview calculations.
 *
 * Usage (from React components):
 *   const worker = new Worker(new URL('./stats.worker.ts', import.meta.url));
 *   worker.postMessage({ type: 'DESCRIPTIVES_PREVIEW', data: [...] });
 *   worker.onmessage = (e) => console.log(e.data);
 */

type WorkerMessage =
  | { type: "DESCRIPTIVES_PREVIEW"; data: number[] }
  | { type: "FREQUENCIES_PREVIEW"; data: (string | number | null)[] }
  | { type: "CORRELATION_PREVIEW"; data: { x: number[]; y: number[] } };

type WorkerResponse =
  | { type: "DESCRIPTIVES_RESULT"; n: number; mean: number; std: number; min: number; max: number }
  | { type: "FREQUENCIES_RESULT"; counts: Record<string, number>; total: number }
  | { type: "CORRELATION_RESULT"; r: number; n: number }
  | { type: "ERROR"; message: string };

// ── Utility functions ─────────────────────────────────────────────────────────

function mean(arr: number[]): number {
  if (arr.length === 0) return NaN;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function std(arr: number[], m?: number): number {
  if (arr.length < 2) return NaN;
  const mu = m ?? mean(arr);
  const variance = arr.reduce((acc, x) => acc + (x - mu) ** 2, 0) / (arr.length - 1);
  return Math.sqrt(variance);
}

function pearsonR(x: number[], y: number[]): number {
  const n = Math.min(x.length, y.length);
  if (n < 2) return NaN;
  const mx = mean(x.slice(0, n));
  const my = mean(y.slice(0, n));
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < n; i++) {
    const xi = x[i] - mx;
    const yi = y[i] - my;
    num += xi * yi;
    dx += xi * xi;
    dy += yi * yi;
  }
  const denom = Math.sqrt(dx * dy);
  return denom === 0 ? NaN : num / denom;
}

// ── Message handler ───────────────────────────────────────────────────────────

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
  const msg = event.data;

  try {
    switch (msg.type) {
      case "DESCRIPTIVES_PREVIEW": {
        const validData = msg.data.filter((v) => v !== null && !isNaN(v));
        if (validData.length === 0) {
          self.postMessage({ type: "ERROR", message: "No valid data" } as WorkerResponse);
          return;
        }
        const sorted = [...validData].sort((a, b) => a - b);
        const m = mean(validData);
        self.postMessage({
          type: "DESCRIPTIVES_RESULT",
          n: validData.length,
          mean: m,
          std: std(validData, m),
          min: sorted[0],
          max: sorted[sorted.length - 1],
        } as WorkerResponse);
        break;
      }

      case "FREQUENCIES_PREVIEW": {
        const counts: Record<string, number> = {};
        let total = 0;
        for (const val of msg.data) {
          if (val === null || val === undefined) continue;
          const key = String(val);
          counts[key] = (counts[key] ?? 0) + 1;
          total++;
        }
        self.postMessage({ type: "FREQUENCIES_RESULT", counts, total } as WorkerResponse);
        break;
      }

      case "CORRELATION_PREVIEW": {
        const { x, y } = msg.data;
        const pairs: [number, number][] = [];
        for (let i = 0; i < Math.min(x.length, y.length); i++) {
          if (isFinite(x[i]) && isFinite(y[i])) {
            pairs.push([x[i], y[i]]);
          }
        }
        const r = pearsonR(
          pairs.map(([xi]) => xi),
          pairs.map(([, yi]) => yi)
        );
        self.postMessage({ type: "CORRELATION_RESULT", r, n: pairs.length } as WorkerResponse);
        break;
      }

      default:
        self.postMessage({ type: "ERROR", message: `Unknown message type` } as WorkerResponse);
    }
  } catch (err) {
    self.postMessage({
      type: "ERROR",
      message: err instanceof Error ? err.message : "Worker computation failed",
    } as WorkerResponse);
  }
};

export {};
