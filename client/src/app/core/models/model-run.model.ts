export interface ModelRun {
  model_run_id: number;
  model_version: string;
  quantized: boolean;
  size_kb: number | null;
  avg_latency_ms: number | null;
  accuracy: number | null;
  created_at: string;
}
