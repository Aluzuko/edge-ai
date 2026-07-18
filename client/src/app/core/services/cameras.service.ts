import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Camera } from '../models/camera.model';

@Injectable({ providedIn: 'root' })
export class CamerasService {
  constructor(private api: ApiService) {}

  list() {
    return this.api.get<Camera[]>('/cameras');
  }
}
