import json, re
from pathlib import Path
root=Path(__file__).resolve().parents[2];ui=root/'outputs/global_trade_intelligence'
assets={}
for name in ['index.html','app.js','metrics.mjs','style.css','world.geojson']:
 value=(ui/name).read_text()
 if name=='app.js':
  value=value.replace('Connected Excel workbook','Cloud-connected workbook').replace('Edit and save this original file, then Refresh.','Edit the Google Sheet; changes sync to the database and the hosted dashboard refreshes on its next scheduled model update.').replace('Original source path','Operational source')
  value+="""
async function syncDashboard(){
 const button=$('#sync-dashboard');
 button.disabled=true;
 try{
  const baseline=model?.meta?.refreshedAt;
  const response=await fetch('/api/sync',{method:'POST'});
  const result=await response.json();
  if(!response.ok)throw Error(result.error||'Could not start sync.');
  $('#refresh-state').textContent='● SYNC QUEUED';
  for(let attempt=0;attempt<36;attempt++){
   await new Promise(resolve=>setTimeout(resolve,5000));
   const latest=await fetch('/api/data',{cache:'no-store'});
   if(latest.ok){
    const updated=await latest.json();
    if(updated.meta.refreshedAt&&updated.meta.refreshedAt!==baseline){
     await refresh();
     return;
    }
   }
  }
  $('#refresh-state').textContent='● SYNC NOT YET CONFIRMED';
  toast('The dashboard has not received an updated model yet.');
 }catch(error){
  $('#refresh-state').textContent='● SYNC UNAVAILABLE';
  toast(error.message);
 }finally{button.disabled=false;}
}
$('#sync-dashboard').onclick=syncDashboard;
setInterval(()=>{if(!$('#sync-dashboard').disabled&&!$('#refresh').disabled)refresh();},60000);
"""
 if name=='app.js':
  value=value.replace('Update the corresponding source table in Excel, save, then Refresh.','Update the Google Sheet. The cloud model refreshes every 30 minutes; click Refresh to load its latest version.').replace('Edit the source row in Excel, save, then Refresh this dashboard.','Edit the corresponding Google Sheet row. Changes appear after cloud synchronization and the scheduled model refresh.').replace('Saved workbook reloaded. Views recalculated.','Latest cloud model loaded. Views recalculated.').replace('Close any incomplete save operation in Excel, then click Refresh.','Check the private GitHub operations workflow, then click Refresh.').replace('Copy file path','Copy source description').replace('Original workbook path copied.','Source description copied.')
  value=re.sub(r'This application is served on <code>127\.0\.0\.1</code>;.*?Launch Dashboard\.command</code>\.', 'This dashboard uses owner-private Sites sign-in. Google Sheets edits synchronize to Supabase, and GitHub refreshes the dashboard model every 30 minutes. The XLSX button downloads the latest daily native Excel backup. Backup copies in private GitHub artifacts are retained for 30 days.',value)
 if name=='index.html':
  value=value.replace('<button id="refresh"', '<button id="sync-dashboard" title="Request a dashboard sync">↻ <span>Sync</span></button><button id="refresh"',1)
  for old,new in [('LOCAL WORKBOOK ENGINE','CLOUD WORKBOOK ENGINE'),('LOCAL DATA CONNECTION','CLOUD DATA CONNECTION'),('SOURCE: EXCEL','SOURCE: GOOGLE SHEETS'),('Show the original workbook location','Show the operational source'),('Reread the saved workbook','Load the latest cloud model'),('Download an XLSX copy. Refresh reads the original workbook shown under Source.','Download the latest daily native Excel backup.')]:value=value.replace(old,new)
 assets['/' if name=='index.html' else '/'+name]=value
worker=(Path(__file__).resolve().parents[1]/'worker/template.js').read_text()
(Path(__file__).resolve().parents[1]/'worker/index.js').write_text('const ASSETS='+json.dumps(assets)+';\n'+worker)
