import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, themeQuartz } from 'ag-grid-community';
import { RequestsService } from '../../core/services/requests.service';
import { SpeciesService } from '../../core/services/species.service';
import { CamerasService } from '../../core/services/cameras.service';
import { RangersService } from '../../core/services/rangers.service';
import { RequestRecord } from '../../core/models/request.model';
import { Species } from '../../core/models/species.model';
import { Camera } from '../../core/models/camera.model';
import { Ranger } from '../../core/models/ranger.model';
import { StatusBadgeComponent } from '../../components/status-badge/status-badge.component';
import { MarkSeenActionCellComponent } from '../../components/mark-seen-action-cell/mark-seen-action-cell.component';

@Component({
  selector: 'app-requests-page',
  standalone: true,
  imports: [CommonModule, FormsModule, AgGridAngular],
  templateUrl: './requests-page.component.html'
})
export class RequestsPageComponent implements OnInit {
  requests: RequestRecord[] = [];
  species: Species[] = [];
  cameras: Camera[] = [];
  rangers: Ranger[] = [];

  newRequest: { ranger_id: number | null; species_id: number | null; camera_id: number | null } = {
    ranger_id: null,
    species_id: null,
    camera_id: null
  };
  statusFilter = '';
  creating = false;
  errorMessage = '';
  theme = themeQuartz;

  colDefs: ColDef[] = [
    { field: 'status', headerName: 'Status', cellRenderer: StatusBadgeComponent, width: 120 },
    { field: 'species_id', headerName: 'Species', flex: 1, valueFormatter: p => this.speciesName(p.value) },
    { field: 'camera_id', headerName: 'Camera', flex: 1, valueFormatter: p => this.cameraName(p.value) },
    { field: 'ranger_id', headerName: 'Ranger', flex: 1, valueFormatter: p => this.rangerName(p.value) },
    { field: 'created_at', headerName: 'Created', flex: 1, valueFormatter: p => p.value ? new Date(p.value).toLocaleString() : '' },
    { field: 'fulfilled_at', headerName: 'Fulfilled', flex: 1, valueFormatter: p => p.value ? new Date(p.value).toLocaleString() : 'Not yet' },
    { headerName: 'Action', cellRenderer: MarkSeenActionCellComponent, width: 140 }
  ];

  gridContext = { onSeen: () => this.loadRequests() };

  constructor(
    private requestsService: RequestsService,
    private speciesService: SpeciesService,
    private camerasService: CamerasService,
    private rangersService: RangersService
  ) {}

  ngOnInit(): void {
    this.speciesService.list().subscribe(s => this.species = s);
    this.camerasService.list().subscribe(c => this.cameras = c);
    this.rangersService.list().subscribe(r => this.rangers = r);
    this.loadRequests();
  }

  loadRequests(): void {
    this.requestsService.list(undefined, this.statusFilter || undefined).subscribe(r => this.requests = r);
  }

  createRequest(): void {
    if (!this.newRequest.ranger_id || !this.newRequest.species_id) {
      return;
    }
    this.creating = true;
    this.errorMessage = '';
    this.requestsService.create({
      ranger_id: this.newRequest.ranger_id,
      species_id: this.newRequest.species_id,
      camera_id: this.newRequest.camera_id
    }).subscribe({
      next: () => {
        this.creating = false;
        this.newRequest = { ranger_id: null, species_id: null, camera_id: null };
        this.loadRequests();
      },
      error: err => {
        this.errorMessage = err.error?.detail ?? 'Could not create request';
        this.creating = false;
      }
    });
  }

  speciesName(id: number): string {
    return this.species.find(s => s.species_id === id)?.common_name ?? String(id);
  }

  cameraName(id: number | null): string {
    if (id === null) {
      return 'Any camera';
    }
    return this.cameras.find(c => c.camera_id === id)?.name ?? String(id);
  }

  rangerName(id: number): string {
    return this.rangers.find(r => r.ranger_id === id)?.name ?? String(id);
  }
}
