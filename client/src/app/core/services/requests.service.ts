import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { RequestRecord, RequestDetail, RequestCreatePayload } from '../models/request.model';

@Injectable({ providedIn: 'root' })
export class RequestsService {
  constructor(private api: ApiService) {}

  list(rangerId?: number, status?: string) {
    return this.api.get<RequestRecord[]>('/requests', { ranger_id: rangerId, status });
  }

  create(payload: RequestCreatePayload) {
    return this.api.post<RequestDetail>('/requests', payload);
  }

  getById(id: number) {
    return this.api.get<RequestDetail>(`/requests/${id}`);
  }

  markSeen(id: number) {
    return this.api.patch<RequestRecord>(`/requests/${id}/seen`);
  }
}
