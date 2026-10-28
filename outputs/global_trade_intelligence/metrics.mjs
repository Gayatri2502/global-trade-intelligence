export const isNum=x=>typeof x==='number'&&Number.isFinite(x);
export const sum=(rows,key)=>rows.reduce((s,x)=>s+(isNum(x[key])?x[key]:0),0);
export const ratio=(a,b)=>isNum(a)&&isNum(b)&&b>0?a/b:null;
export const active=d=>!['Closed','Lost','Invoiced'].includes(d.stage);
export const inYear=(date,year)=>!!date&&(year==='All recorded'||String(date).slice(0,4)===String(year));
const match=(value,selected)=>selected==='All'||String(value||'').toLowerCase().includes(String(selected).toLowerCase());
const searched=(obj,q)=>!q||Object.values(obj).some(v=>typeof v==='string'&&v.toLowerCase().includes(q.toLowerCase()));
export function filterModel(model,s){
 const unambiguous=rows=>{const counts=new Map();rows.forEach(x=>counts.set(x.id,(counts.get(x.id)||0)+1));return rows.filter(x=>x.id&&counts.get(x.id)===1);};
 model={...model,contacts:unambiguous(model.contacts),deals:unambiguous(model.deals),calls:unambiguous(model.calls),cash:unambiguous(model.cash),milestones:unambiguous(model.milestones)};
 let contacts=model.contacts.filter(c=>match(c.product,s.product)&&match(c.role,s.role)&&match(c.priority,s.priority)&&(!s.verified||c.verified)&&(!s.country||c.country===s.country)&&(c.role==='Buyer'?match(c.country,s.destination):match(c.country,s.origin))&&(!c.discovered||s.year==='All recorded'||c.discovered.slice(0,4)<=s.year)&&searched(c,s.q));
 let deals=model.deals.filter(d=>match(d.product,s.product)&&match(d.origin,s.origin)&&match(d.destination,s.destination)&&match(d.stage,s.stage)&&(!s.country||d.origin===s.country||d.destination===s.country));
 const cmap=new Map(model.contacts.map(c=>[c.id,c]));
 if(s.priority!=='All')deals=deals.filter(d=>match(cmap.get(d.buyerId)?.priority,s.priority));
 if(s.role!=='All'||s.verified)deals=deals.filter(d=>contacts.some(c=>c.id===d.buyerId||c.id===d.supplierId));
 if(s.q)deals=deals.filter(d=>searched(d,s.q)||searched(cmap.get(d.buyerId)||{},s.q)||searched(cmap.get(d.supplierId)||{},s.q));
 if(s.stage!=='All'){const linked=new Set(deals.flatMap(d=>[d.buyerId,d.supplierId]));contacts=contacts.filter(c=>linked.has(c.id));}
 const ids=new Set(contacts.map(c=>c.id)),dids=new Set(deals.map(d=>d.id));
 const calls=model.calls.filter(c=>ids.has(c.contactId)&&inYear(c.date,s.year));
 const cash=model.cash.filter(c=>(!c.dealId||dids.has(c.dealId))&&inYear(c.date,s.year));
 const milestones=model.milestones.filter(m=>dids.has(m.dealId));
 const market=model.market.filter(m=>match(m.product,s.product)&&match(m.destination,s.destination)&&(!s.country||m.destination===s.country)&&inYear(m.date,s.year)&&searched(m,s.q));
 return {...model,contacts,deals,calls,cash,milestones,market,periodDeals:deals.filter(d=>inYear(d.invoiceDate,s.year)),periodCommissions:deals.filter(d=>inYear(d.commissionEarnedDate,s.year))};
}
export function summary(data,today=new Date().toISOString().slice(0,10)){
 const buyers=data.contacts.filter(c=>c.role==='Buyer'),suppliers=data.contacts.filter(c=>c.role!=='Buyer');
 const invoices=data.periodDeals.filter(d=>isNum(d.revenue)),costed=invoices.filter(d=>isNum(d.contribution));
 const attempted=data.calls.filter(c=>c.triggered),connected=attempted.filter(c=>c.outcome==='Connected');
 const reachedIds=new Set(connected.map(c=>c.contactId));
 const qualifiedContacts=data.contacts.filter(c=>['Qualified','Sample','Negotiating','Won'].includes(c.stage));
 const qualifiedReached=qualifiedContacts.filter(c=>reachedIds.has(c.id));
 const commissionRows=data.periodCommissions.filter(d=>isNum(d.commissionEarned));
 const receipts=data.cash.filter(c=>c.type==='Receipt'),payments=data.cash.filter(c=>c.type==='Payment');
 return {buyers:buyers.length,suppliers:suppliers.length,verifiedBuyers:buyers.filter(c=>c.verified).length,verifiedSuppliers:suppliers.filter(c=>c.verified).length,buyerVerifiedRate:ratio(buyers.filter(c=>c.verified).length,buyers.length),supplierVerifiedRate:ratio(suppliers.filter(c=>c.verified).length,suppliers.length),active:data.deals.filter(active).length,pipeline:sum(data.deals.filter(active),'pipeline'),pipelineMissing:data.deals.filter(d=>active(d)&&!isNum(d.pipeline)).length,invoices:invoices.length,invoiceRevenue:invoices.length?sum(invoices,'revenue'):null,contribution:costed.length&&costed.length===invoices.length?sum(costed,'contribution'):null,costCoverage:costed.length,customerCash:receipts.some(c=>c.category!=='Commission receipt')||payments.some(c=>c.category==='Customer refund')?sum(receipts.filter(c=>c.category!=='Commission receipt'),'amount')-sum(payments.filter(c=>c.category==='Customer refund'),'amount'):null,cashIn:receipts.length&&receipts.every(c=>isNum(c.amount))?sum(receipts,'amount'):null,cashOut:payments.length&&payments.every(c=>isNum(c.amount))?sum(payments,'amount'):null,commissionEarned:commissionRows.length?sum(commissionRows,'commissionEarned'):null,commissionReceived:receipts.some(c=>c.category==='Commission receipt')||payments.some(c=>c.category==='Commission refund')?sum(receipts.filter(c=>c.category==='Commission receipt'),'amount')-sum(payments.filter(c=>c.category==='Commission refund'),'amount'):null,commissionOutstanding:sum(data.deals,'commissionOutstanding'),receivables:sum(data.deals,'receivable'),overdueReceivables:sum(data.deals.filter(d=>d.invoiceDue&&d.invoiceDue<today),'receivable'),calls:attempted.length,connections:connected.length,connectionRate:ratio(connected.length,attempted.length),decisionMakers:attempted.filter(c=>c.decisionMaker==='Yes').length,decisionCoverage:attempted.filter(c=>['Yes','No'].includes(c.decisionMaker)).length,qualified:qualifiedContacts.length,qualificationRate:ratio(qualifiedReached.length,reachedIds.size),followups:data.contacts.filter(c=>c.nextFollowup&&c.nextFollowup<=today&&!c.excluded),overdueFollowups:data.contacts.filter(c=>c.nextFollowup&&c.nextFollowup<today&&!c.excluded).length,completed:data.deals.filter(d=>d.stage==='Closed').length,delayedMilestones:data.milestones.filter(m=>m.due&&m.due<today&&!['Complete','Not applicable'].includes(m.progress)).length,missingDocuments:data.milestones.filter(m=>m.documentRequired&&(!m.document||m.verification!=='Verified')).length,complianceGaps:data.deals.filter(d=>!['Yes','Not applicable'].includes(d.compliance)).length,expiredLicences:data.contacts.filter(c=>c.licenceExpiry&&c.licenceExpiry<today).length};
}
export function risk(d,today=new Date().toISOString().slice(0,10)){
 if(d.invoiceDue&&d.invoiceDue<today&&(d.receivable||0)>0)return{label:'Overdue payment',tone:'bad'};
 if(d.paymentControl==='Failed')return{label:'Payment control failed',tone:'bad'};
 if(!['Yes','Not applicable'].includes(d.compliance))return{label:'Compliance pending',tone:'warn'};
 if(!d.supplierId)return{label:'Supplier link missing',tone:'warn'};
 if(!d.risk||d.risk==='No flagged issue')return{label:'No flagged issue',tone:'good'};
 return{label:d.risk,tone:'warn'};
}
function bucket(date,grain){
 if(!date)return null;const d=new Date(date+'T00:00:00Z');if(Number.isNaN(d.getTime()))return null;
 const y=d.getUTCFullYear(),m=d.getUTCMonth();
 if(grain==='year')return{key:''+y,label:''+y};
 if(grain==='quarter')return{key:`${y}-${Math.floor(m/3)+1}`,label:`Q${Math.floor(m/3)+1} ${y}`};
 if(grain==='week'){d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));return{key:d.toISOString().slice(0,10),label:d.toLocaleDateString('en-GB',{day:'2-digit',month:'short',timeZone:'UTC'})};}
 return{key:`${y}-${String(m+1).padStart(2,'0')}`,label:d.toLocaleDateString('en-GB',{month:'short',year:'2-digit',timeZone:'UTC'})};
}
export function performance(data,s){
 let events=[],names=[],unit='INR',title='',coverage='',projected=false;
 if(s.metric==='finance'){
  title='Invoice revenue / direct trade contribution';names=['Invoiced revenue','Direct trade contribution'];
  data.periodDeals.forEach(d=>{if(isNum(d.revenue))events.push({date:d.invoiceDate,a:d.revenue,b:d.contribution});});
  coverage=`${data.periodDeals.filter(d=>isNum(d.revenue)).length} valid invoices · ${data.periodDeals.filter(d=>isNum(d.contribution)).length} with complete direct costs. Invoiced sales differ from cash collections.`;
 }else if(s.metric==='cash'){
  title='Actual cash inflows / outflows';names=['Cash inflows','Cash outflows'];events=data.cash.filter(c=>isNum(c.amount)).map(c=>({date:c.date,a:c.type==='Receipt'?c.amount:0,b:c.type==='Payment'?c.amount:0}));coverage='Actual cash dates and recorded transaction FX. Receipts may include customer advances.';
 }else if(s.metric==='calls'){
  title='Calling and outreach activity';names=['Calls attempted','Connected calls'];unit='calls';events=data.calls.filter(c=>c.triggered).map(c=>({date:c.date,a:1,b:c.outcome==='Connected'?1:0}));coverage='Only calls marked Triggered = Yes are included. Connection rate uses attempted calls as the denominator.';
 }else if(s.metric==='qualified'){
  title='Dated lead qualifications';names=['Qualified leads'];unit='leads';events=data.contacts.filter(c=>c.qualifiedDate&&inYear(c.qualifiedDate,s.year)).map(c=>({date:c.qualifiedDate,a:1,b:null}));coverage=`${data.contacts.filter(c=>['Qualified','Sample','Negotiating','Won'].includes(c.stage)&&!c.qualifiedDate).length} qualified-stage contacts lack a qualification date; they are excluded from this historical trend.`;
 }else if(s.metric==='completed'){
  title='Completed deals';names=['Completed deals'];unit='deals';events=data.deals.filter(d=>d.stage==='Closed'&&d.completedDate&&inYear(d.completedDate,s.year)).map(d=>({date:d.completedDate,a:1,b:null}));coverage='Uses Completed date on Closed deals. Closed records without a completion date cannot be placed on a timeline.';
 }else if(s.metric==='commission'){
  title='Commission earned / cash received';names=['Commission earned','Commission received'];events=data.periodCommissions.filter(d=>isNum(d.commissionEarned)).map(d=>({date:d.commissionEarnedDate,a:d.commissionEarned,b:0})).concat(data.cash.filter(c=>((c.type==='Receipt'&&c.category==='Commission receipt')||(c.type==='Payment'&&c.category==='Commission refund'))&&isNum(c.amount)).map(c=>({date:c.date,a:0,b:c.amount*(c.type==='Receipt'?1:-1)})));coverage='Earned commission requires the contract amount, FX and earned date; receipts use the dedicated ledger category.';
 }else{
  projected=true;unit=s.metric==='active'?'opportunities':'INR';names=s.metric==='active'?['Active opportunities']:['Weighted pipeline','Unweighted expected value'];title=s.metric==='active'?'Current opportunities by expected close':'Projected pipeline by expected close';
  events=data.deals.filter(d=>active(d)&&d.expectedClose&&inYear(d.expectedClose,s.year)).map(d=>({date:d.expectedClose,a:s.metric==='active'?1:d.pipeline,b:s.metric==='active'?null:d.expectedValue}));coverage='Current pipeline snapshot grouped by expected close date. This is a projection, not historical realized performance.';
 }
 events=events.filter(e=>e.date&&isNum(e.a));const bins=new Map();
 if(s.grain==='month'&&s.year!=='All recorded')for(let m=1;m<=12;m++){const b=bucket(`${s.year}-${String(m).padStart(2,'0')}-01`,'month');bins.set(b.key,{...b,a:0,b:0,hasA:false,hasB:false});}
 events.forEach(e=>{const b=bucket(e.date,s.grain);if(!b)return;if(!bins.has(b.key))bins.set(b.key,{...b,a:0,b:0,hasA:false,hasB:false});const x=bins.get(b.key);x.a+=e.a;x.hasA=true;if(isNum(e.b)){x.b+=e.b;x.hasB=true;}else if(s.metric==='finance'){x.incompleteB=true;}});
 const rows=[...bins.values()].sort((a,b)=>a.key.localeCompare(b.key));rows.forEach(r=>{if(r.incompleteB){r.hasB=false;r.b=null;}});
 return{rows,names,unit,title,coverage,projected,eventCount:events.length,totalA:events.length?events.reduce((v,e)=>v+e.a,0):null,totalB:s.metric==='finance'&&events.some(e=>!isNum(e.b))?null:events.some(e=>isNum(e.b))?events.reduce((v,e)=>v+(e.b||0),0):null};
}
