import { Component, OnInit } from '@angular/core';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, themeQuartz } from 'ag-grid-community';
import { ModelRunsService } from '../../core/services/model-runs.service';
import { ModelRun } from '../../core/models/model-run.model';

@Component({
  selector: 'app-model-runs-page',
  standalone: true,
  imports: [AgGridAngular],
  templateUrl: './model-runs-page.component.html'
})
export class ModelRunsPageComponent implements OnInit {
  rowData: ModelRun[] = [];
  theme = themeQuartz;

  colDefs: ColDef[] = [
    { field: 'model_version', headerName: 'Version', flex: 1 },
    { field: 'quantized', headerName: 'Quantized', width: 120, valueFormatter: p => p.value ? 'Yes' : 'No' },
    { field: 'size_kb', headerName: 'Size (KB)', width: 130, valueFormatter: p => p.value != null ? p.value.toFixed(0) : '' },
    { field: 'avg_latency_ms', headerName: 'Avg latency (ms)', width: 160, valueFormatter: p => p.value != null ? p.value.toFixed(2) : '' },
    { field: 'accuracy', headerName: 'Accuracy', width: 120, valueFormatter: p => p.value != null ? (p.value * 100).toFixed(1) + '%' : '' },
    { field: 'created_at', headerName: 'Created', flex: 1, valueFormatter: p => p.value ? new Date(p.value).toLocaleString() : '' }
  ];

  constructor(private modelRunsService: ModelRunsService) {}

  ngOnInit(): void {
    this.modelRunsService.list().subscribe(r => this.rowData = r);
  }
}
