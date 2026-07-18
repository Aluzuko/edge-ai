import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Species } from '../models/species.model';

@Injectable({ providedIn: 'root' })
export class SpeciesService {
  constructor(private api: ApiService) {}

  list() {
    return this.api.get<Species[]>('/species');
  }
}
