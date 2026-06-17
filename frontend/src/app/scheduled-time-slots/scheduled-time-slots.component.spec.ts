import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScheduledTimeSlotsComponent } from './scheduled-time-slots.component';

describe('ScheduledTimeSlotsComponent', () => {
  let component: ScheduledTimeSlotsComponent;
  let fixture: ComponentFixture<ScheduledTimeSlotsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ScheduledTimeSlotsComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ScheduledTimeSlotsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
