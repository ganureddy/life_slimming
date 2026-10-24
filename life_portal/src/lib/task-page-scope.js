import { request } from '../api/http';

// Compatibility boundary for the preserved task controller. Everything belongs
// to this page instance: no window.frappe, document patching or shared handlers.
export function createTaskPageScope({ root, session, status, dialogs }) {
  const realDocument = root.ownerDocument, realWindow = realDocument.defaultView;
  const timers = new Set(), listeners = new Set(), inserted = new Set();
  const reads = new Set(), operations = new Set(), errors = new Map();
  let disposed = false;
  const isRead = method => ['frappe.client.get', 'frappe.client.get_list', 'frappe.desk.search.search_link'].includes(method);
  const updateError = () => { status.error = [...new Set(errors.values())].join(' '); };
  const setTimeout = (callback, delay, ...args) => {
    const id = realWindow.setTimeout(() => {
      timers.delete(id);
      if (!disposed) callback(...args);
    }, delay);
    timers.add(id); return id;
  };
  const clearTimeout = id => { timers.delete(id); realWindow.clearTimeout(id); };
  function listen(target, name, handler, options) {
    target.addEventListener(name, handler, options);
    listeners.add({ target, name, handler, options });
  }
  function unlisten(target, name, handler, options) {
    target.removeEventListener(name, handler, options);
    for (const entry of listeners) if (entry.target === target && entry.name === name && entry.handler === handler) listeners.delete(entry);
  }
  function append(parent, node) {
    for (const entry of inserted) if (entry.isConnected === false) inserted.delete(entry);
    inserted.add(node); return parent.appendChild(node);
  }
  const document = {
    querySelector: selector => root.matches(selector) ? root : root.querySelector(selector),
    querySelectorAll: selector => root.querySelectorAll(selector),
    getElementById: id => root.id === id ? root : root.querySelector('#' + realWindow.CSS.escape(id)) || [...inserted].find(node => node.id === id && node.isConnected !== false) || null,
    createElement: tag => realDocument.createElement(tag),
    addEventListener: (...args) => listen(realDocument, ...args),
    removeEventListener: (...args) => unlisten(realDocument, ...args),
    body: { appendChild: node => append(root, node) },
    head: { appendChild: node => append(realDocument.head, node) },
  };
  async function invoke(method, options = {}) {
    if (disposed) throw new DOMException('Page closed', 'AbortError');
    const read = isRead(method), controller = new AbortController();
    const key = method + '\n' + JSON.stringify(options.args || {});
    errors.delete(key); updateError();
    const counter = read ? 'reads' : 'writes'; status[counter]++;
    if (read) reads.add(controller);
    try {
      return await request(method, { ...options, signal: controller.signal, csrfToken: session.csrf_token });
    } catch (error) {
      if (!disposed && error.name !== 'AbortError') { errors.set(key, error.message); updateError(); }
      throw error;
    } finally {
      reads.delete(controller);
      if (!disposed) status[counter]--;
    }
  }
  function track(promise) {
    operations.add(promise);
    promise.then(() => operations.delete(promise), () => operations.delete(promise));
    return promise;
  }
  function call(options) {
    if (typeof options === 'string') options = { method: options };
    const result = track(invoke(options.method, { args: options.args }).then(body => {
      if (!disposed) options.callback?.(body);
      return body;
    }, error => {
      if (!disposed && error.name !== 'AbortError') options.error?.(error);
      throw error;
    }).catch(error => {
      if (!disposed && error.name !== 'AbortError') {
        errors.set(options.method + '\n' + JSON.stringify(options.args || {}), error.message);
        updateError();
      }
      throw error;
    }).finally(() => { if (!disposed) options.always?.(); }));
    // Frappe callback-style callers do not consume the returned promise.
    if (options.callback || options.error) result.catch(() => {});
    return result;
  }
  const notice = message => { if (!disposed) status.notice = typeof message === 'string' ? message : message?.message || ''; };
  const frappe = {
    call, session: { user: session.user }, csrf_token: session.csrf_token,
    user_roles: [...(session.roles || [])], boot: { user: { roles: [...(session.roles || [])] } },
    user: { has_role: role => session.roles?.includes(role) || false },
    show_alert: notice, msgprint: notice,
    ui: { Dialog: function Dialog(options) { return dialogs.create(options); } },
    prompt(fields, action, title, label) {
      const dialog = dialogs.create({ fields, title, primary_action_label: label,
        primary_action: values => { action(values); dialog.hide(); } });
      dialog.show(); return dialog;
    },
    confirm(message, yes, no) { dialogs.confirm(message, yes, no); },
  };
  const window = { frappe, csrf_token: session.csrf_token, setTimeout, clearTimeout,
    confirm: message => realWindow.confirm(message), clipboardData: realWindow.clipboardData };
  return {
    root, session, document, window, frappe, setTimeout, clearTimeout,
    isActive: () => !disposed,
    setUsers: users => dialogs.setUsers(users),
    upload: formData => track(invoke('upload_file', { formData }).then(body => {
      if (!body.message?.file_url) throw new Error('File upload failed.');
      return body.message;
    })),
    async whenIdle() {
      while (!disposed && operations.size) await Promise.allSettled([...operations]);
      return { ok: !disposed && errors.size === 0 };
    },
    dispose() {
      disposed = true;
      for (const controller of reads) controller.abort();
      for (const id of timers) realWindow.clearTimeout(id);
      for (const entry of listeners) entry.target.removeEventListener(entry.name, entry.handler, entry.options);
      for (const node of inserted) node.remove();
      dialogs.dispose();
      timers.clear(); listeners.clear(); inserted.clear(); operations.clear();
    },
  };
}
