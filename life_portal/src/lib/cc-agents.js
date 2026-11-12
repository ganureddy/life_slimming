export function activeCcAgents(agents = []) {
  return agents.filter(agent => agent.agent && agent.employee_status === 'Active'
    && agent.designation === 'Business Executive'
    && ![0, '0', false].includes(agent.user_enabled));
}
