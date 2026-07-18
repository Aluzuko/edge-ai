import { Routes } from '@angular/router';
import { CamerasPageComponent } from './pages/cameras-page/cameras-page.component';
import { DetectionsPageComponent } from './pages/detections-page/detections-page.component';
import { ImageUploadPageComponent } from './pages/image-upload-page/image-upload-page.component';
import { ModelRunsPageComponent } from './pages/model-runs-page/model-runs-page.component';
import { RangersPageComponent } from './pages/rangers-page/rangers-page.component';
import { RequestsPageComponent } from './pages/requests-page/requests-page.component';

export const routes: Routes = [
  { path: '', redirectTo: 'detections', pathMatch: 'full' },
  { path: 'detections', component: DetectionsPageComponent },
  { path: 'cameras', component: CamerasPageComponent },
  { path: 'upload', component: ImageUploadPageComponent },
  { path: 'requests', component: RequestsPageComponent },
  { path: 'rangers', component: RangersPageComponent },
  { path: 'model-runs', component: ModelRunsPageComponent },
];
