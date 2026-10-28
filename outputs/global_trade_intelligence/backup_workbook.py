"""Create and verify an immutable local workbook backup; never overwrites the source."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, tempfile, zipfile
from workbook_data import WORKBOOK, read_workbook

def backup(source=WORKBOOK, destination=None):
    source=Path(source)
    directory=Path(destination) if destination else source.parent/'backups'
    directory.mkdir(parents=True,exist_ok=True)
    payload=source.read_bytes()
    with zipfile.ZipFile(source) as workbook:
        if workbook.testzip():raise ValueError('Source XLSX archive failed integrity check')
    digest=hashlib.sha256(payload).hexdigest()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=directory/(source.stem+'_'+stamp+'_'+digest[:12]+'.xlsx')
    with target.open('xb') as handle:
        handle.write(payload);handle.flush();os.fsync(handle.fileno())
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('Backup checksum mismatch')
    # Restore to a fresh temporary path and parse it, rather than trusting copy success.
    with tempfile.TemporaryDirectory() as restore_dir:
        restored=Path(restore_dir)/'restore.xlsx'
        restored.write_bytes(target.read_bytes())
        tables,raw,errors=read_workbook(restored)
        if len(tables)!=13:raise ValueError('Unexpected restored sheet count')
        if errors:raise ValueError('Restored workbook contains cached formula errors')
    manifest={'source':str(source),'backup':str(target),'sha256':digest,'bytes':len(payload),'created_utc':stamp,'restore_test':'passed','sheets':len(tables),'cached_formula_errors':len(errors),'cloud_backup':False}
    target.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',help='An additional drive or synced folder; local default is not offsite protection')
    args=parser.parse_args()
    print(json.dumps(backup(destination=args.destination),indent=2))
