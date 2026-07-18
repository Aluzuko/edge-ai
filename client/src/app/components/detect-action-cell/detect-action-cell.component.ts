import { Component } from '@angular/core';
import { ICellRendererAngularComp } from 'ag-grid-angular';
import { ICellRendererParams } from 'ag-grid-community';
import { ImagesService } from '../../core/services/images.service';

@Component({
  selector: 'app-detect-action-cell',
  standalone: true,
  template: `<button class="btn btn-sm btn-primary" [disabled]="loading" (click)="runDetection()">
    <i class="bi bi-cpu me-1"></i>{{ loading ? 'Running...' : 'Detect' }}
  </button>`
})
export class DetectActionCellComponent implements ICellRendererAngularComp {
  loading = false;
  private params!: ICellRendererParams;

  constructor(private imagesService: ImagesService) {}

  agInit(params: ICellRendererParams): void {
    this.params = params;
  }

  refresh(): boolean {
    return false;
  }

  runDetection(): void {
    this.loading = true;
    this.imagesService.detect(this.params.data.image_id).subscribe({
      next: () => {
        this.loading = false;
        this.params.context?.onDetected?.(this.params.data.image_id);
      },
      error: () => {
        this.loading = false;
      }
    });
  }
}
