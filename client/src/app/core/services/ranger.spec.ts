import { TestBed } from '@angular/core/testing';

import { Ranger } from './ranger';

describe('Ranger', () => {
  let service: Ranger;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Ranger);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
