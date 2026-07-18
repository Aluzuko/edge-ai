import { TestBed } from '@angular/core/testing';

import { ModelRun } from './model-run';

describe('ModelRun', () => {
  let service: ModelRun;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ModelRun);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
