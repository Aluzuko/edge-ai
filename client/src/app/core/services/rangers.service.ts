import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Ranger } from '../models/ranger.model';

@Injectable({ providedIn: 'root' })
export class RangersService {
  constructor(private api: ApiService) {}

  list() {
    return this.api.get<Ranger[]>('/rangers');
  }

  create(payload: { name: string; contact: string | null }) {
    return this.api.post<Ranger>('/rangers', payload);
  }
}
