import { TestBed } from '@angular/core/testing';

import { Species } from './species';

describe('Species', () => {
  let service: Species;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Species);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
