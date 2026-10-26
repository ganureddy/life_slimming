// Preserve source order and the first match used by Array.find.
export function indexRecords(rows, field) {
  const index = new Map();
  for (const row of rows || []) if (!index.has(row[field])) index.set(row[field], row);
  return index;
}

export function groupRecords(rows, field) {
  const groups = new Map();
  for (const row of rows || []) {
    const key = row[field];
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return groups;
}
