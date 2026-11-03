"""Refresh canonical dashboard model; verify independent native XLSX backups."""
import os,sys,json,time,hmac,hashlib,base64,zipfile,io,re,argparse
from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/global_trade_intelligence'))
from workbook_data import load_model
SID='1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0'
ENDPOINT='https://cdnzpncsbxavakbvtgem.supabase.co/functions/v1/trade-sync'
def rpc(kind,**kw):
 body=json.dumps(dict(kind=kind,spreadsheetId=SID,**kw),separators=(',',':')).encode();stamp=str(int(time.time()))
 sig=hmac.new(os.environ['TRADE_OPERATIONS_SECRET'].encode(),stamp.encode()+b'.'+body,hashlib.sha256).hexdigest()
 with urlopen(Request(ENDPOINT,data=body,headers={'Content-Type':'application/json','x-trade-signature':sig,'x-trade-timestamp':stamp}),timeout=60) as r:return json.load(r)
def normalize(snapshot,path):
 tables={};raw={};errors=[]
 for sh in snapshot['sheets']:
  values=sh['values'];forms=sh.get('formulas',[]);name=sh['name'];headers=values[4] if len(values)>4 else [];rows=[];cells={}
  def col(i):
   out=''
   while i:i,n=divmod(i-1,26);out=chr(65+n)+out
   return out
  for ri,row in enumerate(values):
   for ci,v in enumerate(row):
    ref=col(ci+1)+str(ri+1)
    if v not in (None,''):cells[ref]=v
    if isinstance(v,str) and v in ('#REF!','#DIV/0!','#VALUE!','#N/A','#NAME?','#NUM!','#ERROR!'):errors.append(dict(sheet=name,cell=ref,error=v))
  for i,row in enumerate(values[5:],6):
   if row and row[0] not in ('',None):rows.append(dict(zip(map(str,headers),row),_row=i,_sheet=name))
  tables[name]=rows;raw[name]={'cells':cells}
 model=load_model(path,source=(tables,raw,errors))
 discovery=[];seen=set()
 for sh in snapshot['sheets']:
  if sh['name']!='Discovery inbox':continue
  for i,row in enumerate(sh['values'][1:],2):
   if not row or not row[0] or str(row[0]) in seen:continue
   seen.add(str(row[0]));v=lambda j:row[j] if len(row)>j and row[j] not in ('',None) else 'NA'
   discovery.append(dict(id=str(row[0]),name=v(1),role=v(2),product=v(3),country=v(4),phone=v(5),email=v(6),source=v(7),evidence=v(9),verification=v(10),discovered=str(v(11))[:10],notes=v(12),row=i))
 model['discovery']=discovery;model['meta']['coverage']['discovery']=len(discovery)
 return model
def main():
 p=argparse.ArgumentParser();p.add_argument('--backup',action='store_true');p.add_argument('--model-output',type=Path);a=p.parse_args()
 result=rpc('snapshot_read');age=(datetime.now(timezone.utc)-datetime.fromisoformat(result['lastSync'].replace('Z','+00:00'))).total_seconds()
 if age>1200:raise RuntimeError('Workbook sync is stale (>20 minutes)')
 model=normalize(result['snapshot'],Path(__file__).resolve().parents[1]/'data/Trade_Business_Dashboard.xlsx')
 model['meta'].update(workbook='Google Sheets → signed cloud sync',savedAt=result['lastSync'],sourceHash=result['hash'])
 rpc('model_upload',model=model,sourceHash=result['hash']);print('Dashboard refreshed; source records:',model['meta']['coverage'])
 if a.model_output:
  a.model_output.write_text(json.dumps(model))
 if a.backup:
  archive=rpc('backup_read');content=base64.b64decode(archive['content'])
  if hashlib.sha256(content).hexdigest()!=archive['sha256']:raise RuntimeError('Backup checksum mismatch')
  age=(datetime.now(timezone.utc)-datetime.fromisoformat(archive['createdAt'].replace('Z','+00:00'))).total_seconds()
  if age>129600:raise RuntimeError('Native Excel backup is stale (>36 hours)')
  with zipfile.ZipFile(io.BytesIO(content)) as z:
   if z.testzip():raise RuntimeError('Corrupted XLSX archive')
   import xml.etree.ElementTree as ET
   names={n.attrib['name'] for n in ET.fromstring(z.read('xl/workbook.xml')).iter() if n.tag.endswith('}sheet')}
   if not {'Dashboard','Importers','Exporters','Deals','Cash ledger'}<=names:raise RuntimeError('Required sheets missing')
  out=Path('backups');out.mkdir(exist_ok=True);(out/'Trade_Business_Dashboard.xlsx').write_bytes(content)
  (out/'snapshot.json').write_text(json.dumps(result));(out/'manifest.json').write_text(json.dumps(dict(sha256=archive['sha256'],sheets=sorted(names),verifiedAt=datetime.now(timezone.utc).isoformat())))
  print('Independent backup checksum, ZIP integrity and workbook structure verified')
if __name__=='__main__':main()
