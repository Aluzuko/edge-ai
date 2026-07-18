import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { ModelRun } from '../models/model-run.model';

@Injectable({ providedIn: 'root' })
export class ModelRunsService {
  constructor(private api: ApiService) {}

  list() {
    return this.api.get<ModelRun[]>('/model-runs');
  }
}
