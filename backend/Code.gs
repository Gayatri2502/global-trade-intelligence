const TRADE_ID = '1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0';
const TRADE_ENDPOINT = 'https://cdnzpncsbxavakbvtgem.supabase.co/functions/v1/trade-sync';
const RECORD_SHEETS = ['Importers','Exporters','Growers and suppliers','Market watch','Call log','Deals','Milestones','Cash ledger'];

function onOpen() {
 SpreadsheetApp.getUi().createMenu('Database').addItem('Sync now','tradeSyncNow').addItem('Sync status','tradeSyncStatus').addToUi();
}
function installTradeSync() {
 const props=PropertiesService.getScriptProperties();
 if(!props.getProperty('TRADE_SIGNING_SECRET')) throw new Error('Set TRADE_SIGNING_SECRET in Project Settings → Script properties first.');
 const names=['tradeOnEdit','tradeOnChange','tradeReconcile'];
 ScriptApp.getProjectTriggers().filter(t=>names.includes(t.getHandlerFunction())).forEach(t=>ScriptApp.deleteTrigger(t));
 ScriptApp.newTrigger('tradeOnEdit').forSpreadsheet(TRADE_ID).onEdit().create();
 ScriptApp.newTrigger('tradeOnChange').forSpreadsheet(TRADE_ID).onChange().create();
 ScriptApp.newTrigger('tradeReconcile').timeBased().everyMinutes(5).create();
 tradeSyncNow();
}
function tradeOnEdit(e) { tradeSend_({type:'EDIT',sheetId:String(e.range.getSheet().getSheetId()),range:e.range.getA1Notation()}); }
function tradeOnChange(e) { tradeSend_({type:e.changeType||'CHANGE'}); }
function tradeReconcile() { tradeSend_({type:'RECONCILE'}); }
function tradeSyncNow() { tradeSend_({type:'MANUAL'}); }
function tradeSend_(event) {
 const props=PropertiesService.getScriptProperties(), lock=LockService.getScriptLock();
 if(!lock.tryLock(3000)){props.setProperty('TRADE_PENDING','true');return;}
 try {
  SpreadsheetApp.flush();
  const workbook=SpreadsheetApp.openById(TRADE_ID);
  let cells=0;
  const sheets=workbook.getSheets().map(sheet=>{
   const range=sheet.getDataRange(), values=range.getValues(), formulas=range.getFormulas();
   cells+=range.getNumRows()*range.getNumColumns();
   if(cells>350000)throw new Error('Workbook exceeds sync safety limit; increase only after reviewing payload size.');
   const records=[];const seen=new Set();
   if(RECORD_SHEETS.includes(sheet.getName())) for(let i=5;i<values.length;i++){
    if(values[i][0]===''||values[i][0]===null)continue;
    const id=String(values[i][0]);
    if(seen.has(id))throw new Error('Duplicate record ID in '+sheet.getName()+': '+id);
    seen.add(id);records.push({id,values:values[i],formulas:formulas[i]});
   }
   return {sheetId:String(sheet.getSheetId()),name:sheet.getName(),values,formulas,records};
  });
  const version=Math.max(Date.now(),Number(props.getProperty('TRADE_VERSION')||0)+1);
  const body=JSON.stringify({spreadsheetId:TRADE_ID,version,event,sheets});
  const secret=props.getProperty('TRADE_SIGNING_SECRET');if(!secret)throw new Error('Signing secret is missing');
  const timestamp=String(Math.floor(Date.now()/1000));
  const signature=Utilities.computeHmacSha256Signature(timestamp+'.'+body,secret,Utilities.Charset.UTF_8).map(b=>('0'+(b&255).toString(16)).slice(-2)).join('');
  // Keep a stable version for retries. The backend rejects stale deliveries.
  props.setProperty('TRADE_VERSION',String(version));
  let response;
  for(let attempt=0;attempt<3;attempt++){
   response=UrlFetchApp.fetch(TRADE_ENDPOINT,{method:'post',contentType:'application/json',payload:body,headers:{'x-trade-signature':signature,'x-trade-timestamp':timestamp},muteHttpExceptions:true});
   if(response.getResponseCode()<500)break;Utilities.sleep(1000*(attempt+1));
  }
  if(response.getResponseCode()!==200)throw new Error('Database sync failed: HTTP '+response.getResponseCode());
  const result=JSON.parse(response.getContentText());if(!result.ok)throw new Error('Database rejected sync');
  if(result.discovery && result.discovery.length)tradeImportDiscovery_(workbook,result.discovery,secret);
  props.setProperties({TRADE_LAST_SYNC:new Date().toISOString(),TRADE_LAST_ERROR:'',TRADE_PENDING:'false',TRADE_LAST_RESULT:JSON.stringify(result)});
 }catch(error){props.setProperty('TRADE_LAST_ERROR',String(error));props.setProperty('TRADE_PENDING','true');throw error;}
 finally{lock.releaseLock();}
}
function tradeSyncStatus(){const p=PropertiesService.getScriptProperties();SpreadsheetApp.getUi().alert('Last successful sync: '+(p.getProperty('TRADE_LAST_SYNC')||'Never')+'\nPending: '+(p.getProperty('TRADE_PENDING')||'Unknown')+'\nLast error: '+(p.getProperty('TRADE_LAST_ERROR')||'None'));}

function tradeImportDiscovery_(workbook,leads,secret){
 let inbox=workbook.getSheetByName('Discovery inbox');
 if(!inbox){inbox=workbook.insertSheet('Discovery inbox');inbox.appendRow(['Discovery ID','Company','Role claim','Product','Country','Business phone','Business email','Source URL','Social profiles','Evidence','Verification','First seen','Review notes']);inbox.setFrozenRows(1);inbox.getRange(1,1,1,13).setBackground('#17324D').setFontColor('#FFFFFF').setFontWeight('bold');inbox.setColumnWidths(1,13,160);inbox.setColumnWidth(2,240);inbox.setColumnWidth(10,360);}
 const existing=new Set(inbox.getLastRow()>1?inbox.getRange(2,1,inbox.getLastRow()-1,1).getValues().flat().map(String):[]);
 const safe=value=>{const text=String(value==null?'NA':value);return /^[=+@\-]/.test(text)?"'"+text:text;};
 const rows=leads.filter(l=>!existing.has(l.lead_id)).map(l=>[l.lead_id,l.company,l.role,l.product,l.country,l.phone,l.email,l.website,(l.social_urls||[]).join('; '),l.evidence,'Unverified',l.first_seen,''].map(safe));
 if(rows.length)inbox.getRange(inbox.getLastRow()+1,1,rows.length,13).setValues(rows);
 SpreadsheetApp.flush();
 const body=JSON.stringify({kind:'discovery_ack',spreadsheetId:TRADE_ID,lead_ids:leads.map(l=>l.lead_id)}),stamp=String(Math.floor(Date.now()/1000));
 const signature=Utilities.computeHmacSha256Signature(stamp+'.'+body,secret,Utilities.Charset.UTF_8).map(b=>('0'+(b&255).toString(16)).slice(-2)).join('');
 const response=UrlFetchApp.fetch(TRADE_ENDPOINT,{method:'post',contentType:'application/json',payload:body,headers:{'x-trade-signature':signature,'x-trade-timestamp':stamp},muteHttpExceptions:true});
 if(response.getResponseCode()!==200)throw new Error('Discovery receipt acknowledgement failed; next sync will retry without duplicate rows');
}
