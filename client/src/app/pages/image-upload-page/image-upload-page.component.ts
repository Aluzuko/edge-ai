import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CamerasService } from '../../core/services/cameras.service';
import { ImagesService } from '../../core/services/images.service';
import { Camera } from '../../core/models/camera.model';
import { ImageRecord } from '../../core/models/image.model';
import { Detection } from '../../core/models/detection.model';

@Component({
  selector: 'app-image-upload-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './image-upload-page.component.html'
})
export class ImageUploadPageComponent implements OnInit {
  cameras: Camera[] = [];
  selectedCameraId: number | null = null;
  selectedFile: File | null = null;
  uploadedImage: ImageRecord | null = null;
  detectionResult: Detection | null = null;
  uploading = false;
  detecting = false;
  errorMessage = '';

  constructor(private camerasService: CamerasService, private imagesService: ImagesService) {}

  ngOnInit(): void {
    this.camerasService.list().subscribe(c => this.cameras = c);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile = input.files?.[0] ?? null;
  }

  upload(): void {
    if (!this.selectedCameraId || !this.selectedFile) {
      return;
    }
    this.uploading = true;
    this.errorMessage = '';
    this.uploadedImage = null;
    this.detectionResult = null;
    this.imagesService.upload(this.selectedCameraId, this.selectedFile).subscribe({
      next: img => {
        this.uploadedImage = img;
        this.uploading = false;
      },
      error: err => {
        this.errorMessage = err.error?.detail ?? 'Upload failed';
        this.uploading = false;
      }
    });
  }

  runDetection(): void {
    if (!this.uploadedImage) {
      return;
    }
    this.detecting = true;
    this.imagesService.detect(this.uploadedImage.image_id).subscribe({
      next: d => {
        this.detectionResult = d;
        this.detecting = false;
      },
      error: err => {
        this.errorMessage = err.error?.detail ?? 'Detection failed';
        this.detecting = false;
      }
    });
  }

  imageUrl(): string {
    return this.uploadedImage ? this.imagesService.fileUrl(this.uploadedImage.image_id) : '';
  }
}
