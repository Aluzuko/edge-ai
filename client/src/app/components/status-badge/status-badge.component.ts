import { Component } from '@angular/core';
import { ICellRendererAngularComp } from 'ag-grid-angular';
import { ICellRendererParams } from 'ag-grid-community';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  template: `<span class="badge" [class]="badgeClass">{{ value }}</span>`
})
export class StatusBadgeComponent implements ICellRendererAngularComp {
  value = '';
  badgeClass = 'bg-secondary';

  agInit(params: ICellRendererParams): void {
    this.setValue(params);
  }

  refresh(params: ICellRendererParams): boolean {
    this.setValue(params);
    return true;
  }

  private setValue(params: ICellRendererParams): void {
    this.value = params.value;
    this.badgeClass =
      params.value === 'pending' ? 'bg-warning text-dark' :
      params.value === 'seen' ? 'bg-success' :
      params.value === 'expired' ? 'bg-secondary' :
      'bg-light text-dark';
  }
}
