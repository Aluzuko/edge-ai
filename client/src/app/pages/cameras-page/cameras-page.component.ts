import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, themeQuartz } from 'ag-grid-community';
import { CamerasService } from '../../core/services/cameras.service';
import { ImagesService } from '../../core/services/images.service';
import { Camera } from '../../core/models/camera.model';
import { ImageRecord } from '../../core/models/image.model';
import { ImageThumbCellComponent } from '../../components/image-thumb-cell/image-thumb-cell.component';
import { DetectActionCellComponent } from '../../components/detect-action-cell/detect-action-cell.component';

@Component({
  selector: 'app-cameras-page',
  standalone: true,
  imports: [CommonModule, FormsModule, AgGridAngular],
  templateUrl: './cameras-page.component.html'
})
export class CamerasPageComponent implements OnInit {
  cameras: Camera[] = [];
  images: ImageRecord[] = [];
  selectedCamera: Camera | null = null;
  unprocessedOnly = false;
  theme = themeQuartz;

  cameraColDefs: ColDef[] = [
    { field: 'name', headerName: 'Camera', flex: 1 },
    { field: 'location_description', headerName: 'Location', flex: 1 },
    { field: 'latitude', headerName: 'Latitude', width: 120 },
    { field: 'longitude', headerName: 'Longitude', width: 120 }
  ];

  imageColDefs: ColDef[] = [
    { field: 'image_id', headerName: '', cellRenderer: ImageThumbCellComponent, width: 90, sortable: false, filter: false },
    { field: 'file_path', headerName: 'File', flex: 1 },
    { field: 'captured_at', headerName: 'Captured at', flex: 1, valueFormatter: p => p.value ? new Date(p.value).toLocaleString() : '' },
    { headerName: 'Action', cellRenderer: DetectActionCellComponent, width: 140 }
  ];

  gridContext = { onDetected: () => this.loadImages() };

  constructor(private camerasService: CamerasService, private imagesService: ImagesService) {}

  ngOnInit(): void {
    this.camerasService.list().subscribe(c => this.cameras = c);
  }

  onCameraSelected(event: any): void {
    const selectedRows = event.api.getSelectedRows();
    this.selectedCamera = selectedRows[0] ?? null;
    this.loadImages();
  }

  onUnprocessedToggle(): void {
    this.loadImages();
  }

  loadImages(): void {
    debugger;
    if (!this.selectedCamera) {
      this.images = [];
      return;
    }
    debugger;
    const cameraId = this.selectedCamera.camera_id;
    this.imagesService.list(this.unprocessedOnly).subscribe(imgs => {
      this.images = imgs.filter(i => i.camera_id === cameraId);
    });
  }
}
