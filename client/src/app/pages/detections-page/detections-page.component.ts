import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, themeQuartz } from 'ag-grid-community';
import { DetectionsService } from '../../core/services/detections.service';
import { SpeciesService } from '../../core/services/species.service';
import { Detection } from '../../core/models/detection.model';
import { Species } from '../../core/models/species.model';
import { ImageThumbCellComponent } from '../../components/image-thumb-cell/image-thumb-cell.component';

@Component({
  selector: 'app-detections-page',
  standalone: true,
  imports: [CommonModule, FormsModule, AgGridAngular],
  templateUrl: './detections-page.component.html'
})
export class DetectionsPageComponent implements OnInit {
  rowData: Detection[] = [];
  species: Species[] = [];
  selectedSpeciesId: number | null = null;
  theme = themeQuartz;

  colDefs: ColDef[] = [
    { field: 'image_id', headerName: '', cellRenderer: ImageThumbCellComponent, width: 90, sortable: false, filter: false },
    { field: 'species_name', headerName: 'Species', flex: 1 },
    { field: 'confidence', headerName: 'Confidence', width: 130, valueFormatter: p => p.value != null ? (p.value * 100).toFixed(1) + '%' : '' },
    { field: 'inference_time_ms', headerName: 'Inference (ms)', width: 150, valueFormatter: p => p.value != null ? p.value.toFixed(1) : '' },
    { field: 'captured_at', headerName: 'Captured at', flex: 1, valueFormatter: p => p.value ? new Date(p.value).toLocaleString() : '' },
    { field: 'created_at', headerName: 'Detected at', flex: 1, valueFormatter: p => p.value ? new Date(p.value).toLocaleString() : '' }
  ];

  constructor(private detectionsService: DetectionsService, private speciesService: SpeciesService) {}

  ngOnInit(): void {
    this.speciesService.list().subscribe(s => this.species = s);
    this.loadDetections();
  }

  loadDetections(): void {
    this.detectionsService.list(this.selectedSpeciesId ?? undefined).subscribe(d => this.rowData = d);
  }

  onSpeciesChange(): void {
    this.loadDetections();
  }
}
