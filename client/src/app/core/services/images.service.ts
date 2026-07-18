import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { ImageRecord } from '../models/image.model';
import { Detection } from '../models/detection.model';

@Injectable({ providedIn: 'root' })
export class ImagesService {
  constructor(private api: ApiService) {}

  list(unprocessedOnly?: boolean) {
    return this.api.get<ImageRecord[]>('/images', { unprocessed_only: unprocessedOnly });
  }

  upload(cameraId: number, file: File) {
    const formData = new FormData();
    formData.append('camera_id', String(cameraId));
    formData.append('file', file);
    return this.api.post<ImageRecord>('/images', formData);
  }

  detect(imageId: number) {
    return this.api.post<Detection>(`/images/${imageId}/detect`, {});
  }

  fileUrl(imageId: number) {
    return this.api.fileUrl(`/images/${imageId}/file`);
  }
}
