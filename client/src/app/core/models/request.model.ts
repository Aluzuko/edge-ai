export type RequestStatus = 'pending' | 'seen' | 'expired';

export interface RequestRecord {
  request_id: number;
  ranger_id: number;
  species_id: number;
  camera_id: number | null;
  status: RequestStatus;
  created_at: string;
  fulfilled_at: string | null;
  fulfilled_detection_id: number | null;
}

export interface RequestDetail extends RequestRecord {
  species_name: string;
  detection_id: number | null;
  confidence: number | null;
  detected_at: string | null;
  file_path: string | null;
  captured_at: string | null;
  camera_name: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface RequestCreatePayload {
  ranger_id: number;
  species_id: number;
  camera_id: number | null;
}
