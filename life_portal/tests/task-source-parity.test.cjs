const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');

test('Tasks owns its page sources without a legacy Web Page or JSON generator', () => {
  const files = ['src/pages/TaskManagerPage.vue', 'src/controllers/task-manager.js',
    'src/styles/tasks.css', 'src/lib/task-page-scope.js', 'src/components/tasks/TaskDialogHost.vue'];
  for (const file of files) {
    const source = fs.readFileSync(path.join(root, file), 'utf8');
    assert(!/portal_pages|PortalSourcePage|sync-task-source|task-management\.json|<iframe|\beval\s*\(|new Function\s*\(/.test(source), file);
  }
  const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  assert(!pkg.scripts['sync:tasks']);
  assert(!fs.existsSync(path.join(root, 'scripts/sync-task-source.cjs')));
});

test('Task controller retains task, ticket, review and queue actions', () => {
  const controller = fs.readFileSync(path.join(root, 'src/controllers/task-manager.js'), 'utf8');
  for (const name of ['submitTask', 'submitTicket', 'markTaskDone', 'closeTaskAfterReview',
    'reopenTaskAfterReview', 'cancelTaskWithRemark', 'reopenCancelledTaskWithRemark',
    'reassignTaskWithRemark', 'saveTaskAssignerUpdate', 'markTicketResolved',
    'closeTicketAfterReview', 'reopenTicketAfterReview', 'applyBulkQueue']) {
    assert(controller.includes('function ' + name + '('), name);
  }
});
