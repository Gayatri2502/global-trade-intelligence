from workbook_data import read_workbook, load_model, WORKBOOK
from collections import Counter
from pathlib import Path
import json, zipfile, re, xml.etree.ElementTree as ET

backup=WORKBOOK.parent/'archive'/'Trade_Business_Dashboard_before_terminal.xlsx'
before,braw,_=read_workbook(backup)
after,araw,errors=read_workbook(WORKBOOK)
changes=[]
for sheet in ['Importers','Exporters','Growers and suppliers','Call log','Deals','Milestones','Cash ledger','Market watch','Settings','Monthly finance']:
    for cell,value in braw[sheet]['cells'].items():
        if cell in braw[sheet]['formulas']:continue
        if araw[sheet]['cells'].get(cell)!=value:changes.append({'sheet':sheet,'cell':cell,'before':value,'after':araw[sheet]['cells'].get(cell)})
assert not changes, 'Original source constants changed: '+json.dumps(changes[:10])
assert not errors, 'Cached formula errors: '+json.dumps(errors[:10])
model=load_model()
assert len(model['contacts'])==30
assert len({c['id'] for c in model['contacts']})==30
assert all(not model[k] for k in ['calls','deals','cash','milestones','market'])
assert len(after)==13
assert 'Supplier Contact ID' in araw['Deals']['headers'].values()
assert 'Commission outstanding INR' in araw['Deals']['headers'].values()
assert 'Decision maker reached' in araw['Call log']['headers'].values()
assert 'Qualified date' in araw['Importers']['headers'].values()
with zipfile.ZipFile(WORKBOOK) as z:
    charts=[n for n in z.namelist() if re.match(r'xl/(?:drawings/)?charts/chart\d+\.xml$',n)]
    assert len(charts)==4
    xml=next(z.read(n).decode() for n in charts if '$T$46:$T$57' in z.read(n).decode())
    assert '0D1828' in xml.upper(), 'Dark native chart fill missing'
    assert '00D9F5' in xml.upper() and '16D995' in xml.upper()
    assert '$T$46:$T$57' in xml and '$U$46:$U$57' in xml
print(json.dumps({'source_constants_preserved':True,'original_sheets_preserved':13,'contacts':30,'unique_contact_ids':30,'synthetic_transactions_in_deliverable':0,'formula_errors':0,'dark_chart_binding_verified':True,'audit_findings':model['issues']},indent=2))
