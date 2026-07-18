import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Detection } from '../models/detection.model';

@Injectable({ providedIn: 'root' })
export class DetectionsService {
  constructor(private api: ApiService) {}

  list(speciesId?: number, since?: string) {
    return this.api.get<Detection[]>('/detections', { species_id: speciesId, since });
  }
}
