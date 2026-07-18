import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ICellRendererAngularComp } from 'ag-grid-angular';
import { ICellRendererParams } from 'ag-grid-community';
import { RequestsService } from '../../core/services/requests.service';

@Component({
  selector: 'app-mark-seen-action-cell',
  standalone: true,
  imports: [CommonModule],
  template: `<button *ngIf="params.data.status === 'pending'" class="btn btn-sm btn-outline-success" [disabled]="loading" (click)="markSeen()">
    <i class="bi bi-check2 me-1"></i>{{ loading ? 'Saving...' : 'Mark seen' }}
  </button>`
})
export class MarkSeenActionCellComponent implements ICellRendererAngularComp {
  params!: ICellRendererParams;
  loading = false;

  constructor(private requestsService: RequestsService) {}

  agInit(params: ICellRendererParams): void {
    this.params = params;
  }

  refresh(): boolean {
    return false;
  }

  markSeen(): void {
    this.loading = true;
    this.requestsService.markSeen(this.params.data.request_id).subscribe({
      next: () => {
        this.loading = false;
        this.params.context?.onSeen?.();
      },
      error: () => {
        this.loading = false;
      }
    });
  }
}
