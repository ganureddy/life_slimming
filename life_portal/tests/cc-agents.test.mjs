import { test } from 'node:test';
import assert from 'node:assert/strict';
import { activeCcAgents } from '../src/lib/cc-agents.js';

test('assignment recipients are active call-centre agents with enabled accounts', () => {
  const active={agent:'active@example.com',designation:'Business Executive',employee_status:'Active',user_enabled:1};
  const agents=[active,
    {...active,agent:'left@example.com',employee_status:'Left'},
    {...active,agent:'doctor@example.com',designation:'Doctor'},
    {...active,agent:'disabled@example.com',user_enabled:0},
    {...active,agent:'disabled-string@example.com',user_enabled:'0'},
    {...active,agent:''},
  ];
  assert.deepEqual(activeCcAgents(agents),[active]);
  assert.deepEqual(activeCcAgents(),[]);
});
