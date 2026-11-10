// Enquiry dates never replace the stored Lead.creation timestamp.
export function isWebsiteEnquiry(row) {
  return String(row.source || '').trim().toUpperCase() === 'WEBSITE CHAT' ||
    String(row.custom_remarks || '').includes('[NEW WEBSITE CHAT ENQUIRY ');
}
export function enquiryDate(row) {
  const created=String(row.creation || '').slice(0,10);
  const posting=String(row.custom_posting_date || '').slice(0,10);
  return isWebsiteEnquiry(row) && /^\d{4}-\d{2}-\d{2}$/.test(posting) && posting>=created ? posting : created;
}
export function repeatEnquiry(row) {
  return isWebsiteEnquiry(row) && (enquiryDate(row)>String(row.creation || '').slice(0,10) ||
    String(row.custom_remarks || '').includes('[NEW WEBSITE CHAT ENQUIRY '));
}
export function enquiryLabel(row) {
  if(!repeatEnquiry(row)) return '';
  return row.custom_cc_stage==='FOLLOW-UP' || String(row.status || '').toLowerCase()==='followup'
    ? 'New Enquiry · continuing follow-up' : 'New Enquiry · existing lead';
}
export function mergeEnquiryRows(createdRows, postingRows, from, to) {
  return [...new Map([...createdRows,...postingRows.filter(isWebsiteEnquiry)]
    .filter(row=>enquiryDate(row)>=from&&enquiryDate(row)<=to)
    .map(row=>[row.name,row])).values()];
}
export function repeatEnquiryRows(rows, from, to) {
  return [...new Map(rows.filter(row=>repeatEnquiry(row) && enquiryDate(row)>=from && enquiryDate(row)<=to)
    .map(row=>[row.name,row])).values()];
}
