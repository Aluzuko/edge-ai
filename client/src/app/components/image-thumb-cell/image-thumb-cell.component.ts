import { Component } from '@angular/core';
import { ICellRendererAngularComp } from 'ag-grid-angular';
import { ICellRendererParams } from 'ag-grid-community';
import { ImagesService } from '../../core/services/images.service';

@Component({
  selector: 'app-image-thumb-cell',
  standalone: true,
  template: `<img [src]="src" class="img-thumbnail" style="height:48px;width:auto;" alt="thumbnail">`
})
export class ImageThumbCellComponent implements ICellRendererAngularComp {
  src = '';

  constructor(private imagesService: ImagesService) {}

  agInit(params: ICellRendererParams): void {
    this.src = this.imagesService.fileUrl(params.data.image_id);
  }

  refresh(): boolean {
    return false;
  }
}
