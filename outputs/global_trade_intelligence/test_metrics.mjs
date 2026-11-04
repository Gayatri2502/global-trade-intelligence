import assert from 'node:assert/strict';
import {filterModel,summary,performance,ratio,risk} from './metrics.mjs';
// Synthetic fixtures exist only in this test module, never in the user's workbook or dashboard dataset.
const c={id:'SYNTHETIC-C1',name:'Synthetic buyer',role:'Buyer',product:'Moringa',country:'India',priority:'High',stage:'Qualified',verified:true,discovered:'2026-01-01',qualifiedDate:'2026-02-01'};
const d={id:'SYNTHETIC-D1',buyerId:c.id,supplierId:'SYNTHETIC-S1',product:'Moringa',origin:'India',destination:'United Kingdom',stage:'Invoiced',invoiceDate:'2026-02-03',revenue:10000,directCost:5500,contribution:4500,receipts:6000,receivable:4000,invoiceDue:'2026-03-03',expectedValue:10000,pipeline:0,commissionExpected:2000,commissionEarned:2000,commissionReceived:500,commissionOutstanding:1500,commissionEarnedDate:'2026-02-03',compliance:'Yes'};
const model={contacts:[c,{...c,id:'SYNTHETIC-S1',name:'Synthetic supplier',role:'Exporter',country:'India'}],deals:[d],calls:[{id:'SYNTHETIC-A1',contactId:c.id,date:'2026-02-01',triggered:true,outcome:'Connected',decisionMaker:'Yes'},{id:'SYNTHETIC-A2',contactId:c.id,date:'2026-02-02',triggered:true,outcome:'No answer'}],cash:[{id:'SYNTHETIC-X1',dealId:d.id,date:'2026-02-05',type:'Receipt',category:'Customer receipt',amount:6000},{id:'SYNTHETIC-X2',dealId:d.id,date:'2026-02-05',type:'Receipt',category:'Commission receipt',amount:500}],milestones:[],market:[]};
const state={year:'2026',product:'All',origin:'All',destination:'All',role:'All',stage:'All',priority:'All',q:'',country:null,metric:'finance',grain:'month'};
let filtered=filterModel(model,state),s=summary(filtered,'2026-03-10');
assert.equal(s.invoiceRevenue,10000);assert.equal(s.contribution,4500);assert.equal(s.receivables,4000);assert.equal(s.commissionOutstanding,1500);assert.equal(s.commissionReceived,500);assert.equal(s.cashIn,6500);assert.equal(s.customerCash,6000);assert.equal(s.connectionRate,.5);assert.equal(s.qualificationRate,1);assert.equal(risk(d,'2026-03-10').tone,'bad');
assert.equal(performance(filtered,state).totalA,10000);assert.equal(performance(filtered,state).totalB,4500);
assert.equal(performance(filtered,{...state,metric:'calls'}).totalA,2);assert.equal(performance(filtered,{...state,metric:'calls'}).totalB,1);
assert.equal(filterModel(model,{...state,product:'Garlic'}).deals.length,0);
assert.equal(filterModel(model,{...state,stage:'Quote'}).contacts.length,0);
assert.equal(summary(filterModel(model,{...state,year:'2025'})).invoiceRevenue,null);
assert.equal(ratio(null,100),null);assert.equal(ratio(1,0),null);
const missing={...model,deals:[{...d,contribution:null}]};assert.equal(summary(filterModel(missing,state)).contribution,null);assert.equal(performance(filterModel(missing,state),state).totalB,null);
const duplicateCalls={...model,calls:[...model.calls,...model.calls]};assert.equal(summary(filterModel(duplicateCalls,state)).invoiceRevenue,10000);
const refunded={...model,cash:[...model.cash,{id:'SYNTHETIC-R1',dealId:d.id,date:'2026-02-06',type:'Payment',category:'Customer refund',amount:1000},{id:'SYNTHETIC-R2',dealId:d.id,date:'2026-02-06',type:'Payment',category:'Commission refund',amount:100}]};assert.equal(summary(filterModel(refunded,state)).customerCash,5000);assert.equal(summary(filterModel(refunded,state)).commissionReceived,400);assert.equal(performance(filterModel(refunded,state),{...state,metric:'commission'}).totalB,400);
console.log('PASS: invoice/contribution, cash/commission separation, receivables, cohort rates, filters, metric switches, missing-data handling and no deal multiplication. Synthetic fixtures were never written to the workbook.');

const filterFixture={...model,discovery:[
 {id:'D1',name:'Test Buyer',country:'India',role:'Importer',product:'Moringa'},
 {id:'D2',name:'Test Seller',country:'India',role:'Exporter',product:'Moringa powder'}
]};
assert.deepEqual(filterModel(filterFixture,{...state,role:'Buyer',destination:'India',product:'Moringa'}).discovery.map(row=>row.id),['D1']);
assert.equal(filterModel(filterFixture,{...state,year:'2025'}).deals.length,0);
