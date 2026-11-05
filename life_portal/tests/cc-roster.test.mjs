import {test} from 'node:test';
import assert from 'node:assert/strict';
import {movePeriod, summarize, cellLabel} from '../src/lib/cc-roster.js';

test('month navigation handles year and leap boundaries',()=>{
  assert.equal(movePeriod('2026-12-01','month',1),'2027-01-01');
  assert.equal(movePeriod('2024-03-01','month',-1),'2024-02-01');
  assert.equal(movePeriod('2026-11-02','week',-1),'2026-10-26');
});
test('summary separates planned days, week offs, missing data and conflicts',()=>{
  const cells={
    a:{shifts:[{shift_type:'Morning'}],attendance:'Present',leave:false},
    b:{shifts:[{shift_type:'Week Off'}],attendance:'',leave:false},
    c:{shifts:[],attendance:'',leave:false},
    d:{shifts:[{shift_type:'Morning'},{shift_type:'Evening'}],attendance:'Absent',leave:false},
    e:{shifts:[],attendance:'On Leave',leave:true},
  };
  assert.deepEqual(summarize(cells),{planned:1,weekOff:1,unplanned:2,conflicts:1,present:1,absent:1,leave:1});
  assert.equal(cellLabel(cells.c),'Not planned');
  assert.equal(cellLabel(cells.d),'Overlapping shifts');
});
