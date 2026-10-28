import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];ui=root/'outputs/global_trade_intelligence'
assets={}
for name in ['index.html','app.js','metrics.mjs','style.css','world.geojson']:
 value=(ui/name).read_text()
 if name=='app.js':
  value=value.replace('Connected Excel workbook','Cloud-connected workbook').replace('Edit and save this original file, then Refresh.','Edit the Google Sheet; changes sync to the database and the hosted dashboard refreshes on its next scheduled model update.').replace('Original source path','Operational source')
  value+='\nsetInterval(()=>refresh(),60000);\n'
 assets['/' if name=='index.html' else '/'+name]=value
worker=(Path(__file__).resolve().parents[1]/'worker/template.js').read_text()
(Path(__file__).resolve().parents[1]/'worker/index.js').write_text('const ASSETS='+json.dumps(assets)+';\n'+worker)
