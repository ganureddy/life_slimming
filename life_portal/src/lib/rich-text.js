// ERP descriptions remain formatted content; executable elements and link
// protocols are removed before Vue renders the description.
export function sanitizeRichText(value) {
  const document = new DOMParser().parseFromString(String(value || ''), 'text/html');
  document.querySelectorAll('script,style,iframe,object,embed,link,meta,base,form,input,button,textarea,select,svg,math').forEach(node => node.remove());
  for (const node of document.body.querySelectorAll('*')) {
    for (const attribute of [...node.attributes]) {
      const name = attribute.name.toLowerCase();
      if (name.startsWith('on') || ['srcdoc', 'srcset', 'action', 'formaction', 'style'].includes(name)) node.removeAttribute(attribute.name);
      if (['href', 'src', 'xlink:href'].includes(name)) {
        try { const url = new URL(attribute.value, window.location.origin); if (!['http:', 'https:', 'mailto:', 'tel:'].includes(url.protocol)) node.removeAttribute(attribute.name); }
        catch { node.removeAttribute(attribute.name); }
      }
    }
    if (node.tagName === 'A') node.setAttribute('rel', 'noopener noreferrer');
  }
  return document.body.innerHTML;
}
