"""Import a reviewed evidence manifest through the existing signed discovery endpoint.
Use --dry-run to validate without writing. Never prints business contact details.
"""
import argparse,hashlib,json,os,re,sys,uuid
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'crawler'))
from run import signed_post

def validate(rows):
 seen=set()
 for row in rows:
  for key in ('company','role','product','country','phone','email','website','evidence'):
   if not isinstance(row.get(key),str) or not row[key].strip():raise ValueError('Required field missing: '+key)
  p=urlparse(row['website'])
  if p.scheme!='https' or not p.hostname:raise ValueError('Public HTTPS source required')
  # Company identity, not shared catalogue host, so IndiaMART sellers stay separate.
  identity=re.sub(r'[^a-z0-9]','',row['company'].lower())+'|'+row['country'].lower()
  row['lead_id']=row.get('lead_id') or hashlib.sha256(identity.encode()).hexdigest()[:32]
  if row['lead_id'] in seen:raise ValueError('Duplicate lead in manifest')
  seen.add(row['lead_id']);row.setdefault('social_urls',[]);row['status']='Unverified'
 return rows
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--dry-run',action='store_true');args=p.parse_args()
 rows=validate(json.loads(Path(args.manifest).read_text()));config=json.loads(Path(__file__).resolve().parents[1].joinpath('crawler/config.json').read_text())
 if not args.dry_run:
  env=Path(__file__).resolve().parents[1]/'crawler/.env'
  if env.exists():
   for line in env.read_text().splitlines():
    if '=' in line and not line.startswith('#'):k,v=line.split('=',1);os.environ.setdefault(k,v.strip().strip('\"').strip("'"))
  result=signed_post(config,dict(kind='discovery_ingest',spreadsheetId=config['spreadsheet_id'],run_id=str(uuid.uuid4()),leads=rows,summary={'mode':'reviewed_public_evidence','leads':len(rows)}))
  if not result.get('ok'):raise RuntimeError('Import rejected')
 print('Validated contacts:',len(rows),'Mode:','dry-run' if args.dry_run else 'cloud import')
