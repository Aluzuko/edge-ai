export interface Detection {
  detection_id: number;
  image_id: number;
  species_id: number;
  model_run_id: number;
  confidence: number;
  inference_time_ms: number | null;
  created_at: string;
  species_name?: string;
  file_path?: string;
  captured_at?: string;
}
