// Transport outcomes cannot establish a sales outcome. Only explicit dispositions map.
export function portalDisposition(event, workflow) {
  const key = value => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const options = [...new Set(['ACTIVE','SUCCESS','LOST','INVALID','BADNUM','RETRY','VISIT'].flatMap(group => workflow[group] || []))];
  const aliases = { nr: 'No Response', callDisconnected: 'Call Disconnected', callback: 'Callback: Scheduled', dnc: 'Do Not Contact' };
  const mapped = new Map(options.map(value => [key(value), value]));
  for (const [alias, value] of Object.entries(aliases)) if (options.includes(value)) mapped.set(key(alias), value);
  for (const value of [event?.disposition_3, event?.disposition_2, event?.disposition]) {
    if (mapped.has(key(value))) return mapped.get(key(value));
  }
  return '';
}
