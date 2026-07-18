import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, themeQuartz } from 'ag-grid-community';
import { RangersService } from '../../core/services/rangers.service';
import { Ranger } from '../../core/models/ranger.model';

@Component({
  selector: 'app-rangers-page',
  standalone: true,
  imports: [CommonModule, FormsModule, AgGridAngular],
  templateUrl: './rangers-page.component.html'
})
export class RangersPageComponent implements OnInit {
  rangers: Ranger[] = [];
  newRanger = { name: '', contact: '' };
  creating = false;
  errorMessage = '';
  theme = themeQuartz;

  colDefs: ColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1 },
    { field: 'contact', headerName: 'Contact', flex: 1 }
  ];

  constructor(private rangersService: RangersService) {}

  ngOnInit(): void {
    this.loadRangers();
  }

  loadRangers(): void {
    this.rangersService.list().subscribe(r => this.rangers = r);
  }

  createRanger(): void {
    if (!this.newRanger.name.trim()) {
      return;
    }
    this.creating = true;
    this.errorMessage = '';
    this.rangersService.create({ name: this.newRanger.name, contact: this.newRanger.contact || null }).subscribe({
      next: () => {
        this.creating = false;
        this.newRanger = { name: '', contact: '' };
        this.loadRangers();
      },
      error: err => {
        this.errorMessage = err.error?.detail ?? 'Could not create ranger';
        this.creating = false;
      }
    });
  }
}
