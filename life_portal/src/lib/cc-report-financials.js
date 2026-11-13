// ccInvoicePackageSplitTotals: new invoice values and older collections stay separate.
export function packageSplit(rows,from,to){
 const totals={withGst:0,withoutGst:0,paid:0,oldPackagePaid:0,balance:0,newPackageCount:0,oldPackageCount:0};
 for(const row of rows||[]){if(!row.therapy_plan||String(row.therapy_plan_media||'').trim().toLowerCase()!=='call center'||Number(row.therapy_plan_already_taken)===1)continue;const date=String(row.invoice_date||'').slice(0,10),paid=Math.max(0,Number(row.paid||0));if(date&&date>=from&&date<=to){totals.withGst+=Math.max(0,Number(row.with_gst||0));totals.withoutGst+=Math.max(0,Number(row.without_gst||0));totals.paid+=paid;totals.balance+=Math.max(0,Number(row.balance||0));totals.newPackageCount++;}else if(date&&date<from){totals.oldPackagePaid+=paid;totals.oldPackageCount++;}}
 return totals;
}

export function consultantRollingRange(end){const date=new Date(end+'T12:00:00Z');const start=new Date(Date.UTC(date.getUTCFullYear(),date.getUTCMonth()-3,date.getUTCDate()+1,12));return [start.toISOString().slice(0,10),end];}
