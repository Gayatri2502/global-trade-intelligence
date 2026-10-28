"""Read the operational XLSX without rewriting it; no third-party spreadsheet writer."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone
import json, re, zipfile, os, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
_local_workbook = ROOT.parent / 'trade_contacts_20261026' / 'Trade_Business_Dashboard.xlsx'
WORKBOOK = Path(os.environ.get('TRADE_WORKBOOK', str(_local_workbook if _local_workbook.exists() else ROOT.parent.parent / 'data' / 'Trade_Business_Dashboard.xlsx')))
NS = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
CONTACT_SHEETS = ['Importers','Exporters','Growers and suppliers']

def read_workbook(path=WORKBOOK):
    sheets, raw, errors = {}, {}, []
    with zipfile.ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)]
        rels = {n.attrib['Id']:n.attrib['Target'] for n in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',NS):
            name=sheet.attrib['name']; target=rels[sheet.attrib[REL]]
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            grid={}; formulas={}
            for cell in ET.fromstring(z.read(target)).findall('.//s:sheetData/s:row/s:c',NS):
                ref=cell.attrib['r']; typ=cell.attrib.get('t'); v=cell.find('s:v',NS); f=cell.find('s:f',NS)
                val=v.text if v is not None and v.text is not None else None
                if typ=='s': val=shared[int(val)] if val is not None else None
                elif typ=='inlineStr': val=''.join(cell.find('s:is',NS).itertext())
                elif typ not in ['str','e'] and val is not None:
                    try: val=float(val); val=int(val) if val.is_integer() else val
                    except ValueError: pass
                if val not in [None,'']: grid[ref]=val
                if f is not None: formulas[ref]=f.text
                if typ=='e': errors.append({'sheet':name,'cell':ref,'error':val})
            headers={re.sub(r'\d+','',k):v for k,v in grid.items() if re.search(r'\d+$',k)[0]=='5'}
            rows=[]
            for rn in sorted({int(re.search(r'\d+$',k)[0]) for k in grid if int(re.search(r'\d+$',k)[0])>=6}):
                if not grid.get('A'+str(rn)): continue
                rec={'_row':rn,'_sheet':name}
                for col,head in headers.items():
                    value=grid.get(col+str(rn))
                    if isinstance(value,(float,int)) and any(w in str(head).lower() for w in ['date','expiry','next contact recheck','expected close','next follow-up']):
                        if 20000<value<100000: value=(datetime(1899,12,30)+timedelta(days=value)).date().isoformat()
                    rec[str(head)]=value
                rows.append(rec)
            sheets[name]=rows
            raw[name]={'cells':grid,'formulas':formulas,'headers':headers}
    return sheets,raw,errors

def clean(value):
    return value if value not in [None,'','NA','N/A','n.a.'] else None

def num(value):
    return float(value) if isinstance(value,(int,float)) and not isinstance(value,bool) else None

def iso(value):
    if not value:return None
    if isinstance(value,(int,float)):return (datetime(1899,12,30)+timedelta(days=value)).date().isoformat()
    return str(value)[:10] if re.match(r'\d{4}-\d{2}-\d{2}',str(value)) else None

def load_model(path=WORKBOOK):
    tables,raw,formula_errors=read_workbook(path)
    issues=[]; contacts=[]
    for sheet in CONTACT_SHEETS:
        for row in tables.get(sheet,[]):
            c={
                'id':row.get('Contact ID'),'name':row.get('Company'),'role':'Buyer' if sheet=='Importers' else 'Exporter' if sheet=='Exporters' else 'Grower / supplier',
                'product':row.get('Product group'),'country':row.get('Country'),'region':row.get('State / region'),'city':row.get('City'),
                'person':clean(row.get('Contact person')),'phone':clean(row.get('Phone')),'email':clean(row.get('Email')),'source':clean(row.get('Website / source URL')),
                'stage':row.get('Lead stage') or 'New','verified':row.get('Contact verification')=='Verified','verification':row.get('Contact verification') or 'Not checked',
                'priority':row.get('Priority tier') or 'Unassessed','score':num(row.get('Priority score /100')),'discovered':iso(row.get('Research date')),
                'lastVerified':iso(row.get('Last contact verified')),'nextFollowup':iso(row.get('Next follow-up')),'qualifiedDate':iso(row.get('Qualified date')),
                'excluded':row.get('Do not contact')=='Yes','licence':clean(row.get('Published registration IDs')),'licenceStatus':row.get('Licence document status'),
                'licenceExpiry':iso(row.get('Licence expiry')),'evidence':row.get('Source notes'),'ratings':{k:row.get(k) for k in ['Product fit 1–5','Volume fit 1–5','Margin potential 1–5','Payment safety 1–5','Document readiness 1–5','Call rating 1–5']},
                'row':row['_row'],'sheet':sheet,'notes':row.get('Commercial notes'),'capacity':clean(row.get('MOQ / capacity')),'quote':clean(row.get('Quoted price / currency')),
            }
            contacts.append(c)
            if not c['phone'] and not c['email']:issues.append({'severity':'warning','type':'Contact channel missing','id':c['id'],'sheet':sheet,'row':c['row']})
            if c['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',str(c['email'])):issues.append({'severity':'warning','type':'Email needs review','id':c['id'],'sheet':sheet,'row':c['row']})
    for cid,n in Counter(c['id'] for c in contacts).items():
        if n>1:issues.append({'severity':'error','type':'Duplicate contact ID','id':cid,'sheet':'CRM','row':None})
    contact_ids={c['id'] for c in contacts}
    calls=[]
    for r in tables.get('Call log',[]):
        c={'id':r.get('Event ID'),'contactId':r.get('Contact ID'),'date':iso(r.get('Call date')),'channel':r.get('Channel'),'outcome':r.get('Outcome'),'triggered':r.get('Triggered')=='Yes','duration':num(r.get('Duration min')),'notes':r.get('Call notes'),'nextAction':r.get('Next action'),'followup':iso(r.get('Follow-up date')),'owner':r.get('Owner'),'decisionMaker':r.get('Decision maker reached'),'row':r['_row']}
        calls.append(c)
        if c['contactId'] not in contact_ids:issues.append({'severity':'error','type':'Call has unknown contact ID','id':c['id'],'sheet':'Call log','row':c['row']})
    cash=[]
    for r in tables.get('Cash ledger',[]):
        original=num(r.get('Original amount'));fx=num(r.get('FX INR per unit'))
        value=original*fx if original is not None and fx is not None else None
        cash.append({'id':r.get('Cash ID'),'dealId':r.get('Deal ID'),'date':iso(r.get('Date')),'type':r.get('Type'),'category':r.get('Category'),'currency':r.get('Currency'),'amountOriginal':original,'fx':fx,'amount':value,'row':r['_row'],'notes':r.get('Notes')})
        if value is None:issues.append({'severity':'error','type':'Cash amount or FX missing','id':r.get('Cash ID'),'sheet':'Cash ledger','row':r['_row']})
    deals=[]
    cost_fields=['Product cost INR','Packing / processing INR','Origin inland / handling INR','Testing / export documents INR','Insurance INR','International freight INR','Duty / nonrecoverable tax INR','Destination broker / handling INR','Final mile / storage INR','Bank / payment fees INR','Other direct costs INR']
    for r in tables.get('Deals',[]):
        did=r.get('Deal ID');stage=r.get('Stage');inv_amt=num(r.get('Invoice net amount original currency'));fx=num(r.get('FX to INR'));invoice_date=iso(r.get('Invoice date'))
        revenue=inv_amt*fx if stage in ['Invoiced','Closed'] and invoice_date and inv_amt is not None and fx is not None else None
        costs=[num(r.get(k)) for k in cost_fields]; cost=sum(costs) if all(v is not None for v in costs) else None
        trade_events=[x for x in cash if x['dealId']==did and ((x['type']=='Receipt' and x['category']!='Commission receipt') or (x['type']=='Payment' and x['category']=='Customer refund'))]
        receipts=sum((x['amount'] or 0)*(1 if x['type']=='Receipt' else -1) for x in trade_events) if all(x['amount'] is not None for x in trade_events) else None
        expected=num(r.get('Expected revenue INR'));prob=num(r.get('Win probability'))
        pipeline=expected*prob if stage not in ['Lost','Closed','Invoiced'] and expected is not None and prob is not None else 0 if stage in ['Lost','Closed','Invoiced'] else None
        earned_original=num(r.get('Contract commission original'));commission_fx=num(r.get('Commission FX to INR'));earned_date=iso(r.get('Commission earned date'))
        commission=earned_original*commission_fx if earned_date and earned_original is not None and commission_fx is not None else None
        commission_events=[x for x in cash if x['dealId']==did and ((x['type']=='Receipt' and x['category']=='Commission receipt') or (x['type']=='Payment' and x['category']=='Commission refund'))]
        commission_received=sum((x['amount'] or 0)*(1 if x['type']=='Receipt' else -1) for x in commission_events) if all(x['amount'] is not None for x in commission_events) else None
        credit=num(r.get('Commission credit adjustments INR'))
        d={'id':did,'buyerId':r.get('Contact ID'),'supplierId':clean(r.get('Supplier Contact ID')),'direction':r.get('Trade direction'),'product':r.get('Product'),'origin':r.get('Origin country'),'destination':r.get('Destination country'),'stage':stage,'expectedClose':iso(r.get('Expected close date')),'completedDate':iso(r.get('Completed date')),'probability':prob,'expectedValue':expected,'pipeline':pipeline,'invoiceDate':invoice_date,'revenue':revenue,'directCost':cost,'contribution':revenue-cost if revenue is not None and cost is not None else None,'receipts':receipts,'receivable':max(0,revenue-receipts) if revenue is not None and receipts is not None else None,'invoiceDue':iso(r.get('Invoice due date')),'quantity':num(r.get('Quantity')),'unit':r.get('Unit'),'businessModel':r.get('Business model'),'commissionExpected':earned_original*commission_fx if earned_original is not None and commission_fx is not None else None,'commissionEarned':commission,'commissionReceived':commission_received,'commissionOutstanding':max(0,commission-commission_received-(credit or 0)) if commission is not None and commission_received is not None else None,'commissionEarnedDate':earned_date,'commissionDue':iso(r.get('Commission due date')),'compliance':r.get('Import requirements checked'),'paymentControl':r.get('Security / credit check'),'sample':r.get('Product / sample approval'),'nextFollowup':iso(r.get('Next follow-up date')),'risk':r.get('Deal risk summary'),'incoterm':r.get('Incoterm'),'row':r['_row'],'costs':dict(zip(cost_fields,costs)),'documentFolder':clean(r.get('Document folder'))}
        deals.append(d)
        if d['buyerId'] not in contact_ids:issues.append({'severity':'error','type':'Deal has unknown contact ID','id':did,'sheet':'Deals','row':d['row']})
        if d['supplierId'] and d['supplierId'] not in contact_ids:issues.append({'severity':'error','type':'Unknown supplier ID','id':did,'sheet':'Deals','row':d['row']})
        if not d['supplierId']:issues.append({'severity':'warning','type':'Supplier link missing','id':did,'sheet':'Deals','row':d['row']})
        if stage in ['Invoiced','Closed'] and revenue is None:issues.append({'severity':'error','type':'Invoice date, amount or FX missing','id':did,'sheet':'Deals','row':d['row']})
        if prob is not None and not 0<=prob<=1:issues.append({'severity':'error','type':'Probability outside 0–100%','id':did,'sheet':'Deals','row':d['row']})
    deal_ids={d['id'] for d in deals}
    for x in cash:
        if x['dealId'] and x['dealId'] not in deal_ids:issues.append({'severity':'error','type':'Cash has unknown deal ID','id':x['id'],'sheet':'Cash ledger','row':x['row']})
    milestones=[]
    for r in tables.get('Milestones',[]):
        m={'id':r.get('Event ID'),'dealId':r.get('Deal ID'),'contactId':r.get('Contact ID'),'phase':r.get('Trade phase'),'name':r.get('Milestone'),'owner':r.get('Owner'),'due':iso(r.get('Due date')),'completed':iso(r.get('Completed date')),'progress':r.get('Progress'),'documentRequired':r.get('Document required')=='Yes','document':clean(r.get('Document / evidence URL')),'verification':r.get('Evidence verification'),'blocker':r.get('Blocker / next action'),'row':r['_row']}
        milestones.append(m)
        if m['dealId'] not in deal_ids:issues.append({'severity':'error','type':'Milestone has unknown deal ID','id':m['id'],'sheet':'Milestones','row':m['row']})
    market=[]
    for r in tables.get('Market watch',[]):
        market.append({'id':r.get('Market ID'),'date':iso(r.get('Research date')),'destination':r.get('Destination market'),'product':r.get('Product'),'channel':r.get('Buyer channel'),'season':r.get('Season / window'),'signal':r.get('Signal type'),'price':num(r.get('Indicative price')),'currency':r.get('Currency'),'unit':r.get('Unit'),'basis':r.get('Trade basis / Incoterm'),'source':clean(r.get('Price source URL')),'requirement':r.get('Import / product requirement'),'requirementSource':clean(r.get('Requirement source URL')),'status':r.get('Evidence status'),'confirmed':iso(r.get('Last confirmed date')),'notes':r.get('Notes'),'row':r['_row']})
    for f in formula_errors:issues.append({'severity':'error','type':'Formula '+str(f['error']),'id':f['cell'],'sheet':f['sheet'],'row':None})
    for sheet,rows,idfield in [('Deals',deals,'id'),('Call log',calls,'id'),('Cash ledger',cash,'id'),('Milestones',milestones,'id')]:
        for ident,count in Counter(x[idfield] for x in rows).items():
            if count>1:issues.append({'severity':'error','type':'Duplicate record ID','id':ident,'sheet':sheet,'row':None})
    companies={}
    for c in contacts:
        key=re.sub(r'\W','',str(c['name']).lower())+'|'+str(c['country'])
        companies.setdefault(key,[]).append(c['id'])
    for ids in companies.values():
        if len(ids)>1:issues.append({'severity':'review','type':'Company appears more than once; check legitimate multiple roles/products','id':', '.join(ids),'sheet':'CRM','row':None})
    settings={k:v for k,v in raw.get('Settings',{}).get('cells',{}).items() if k in ['B10','B11','B12','B13','E10','E11','E12']}
    return {'contacts':contacts,'calls':calls,'deals':deals,'cash':cash,'milestones':milestones,'market':market,'issues':issues,'settings':settings,'meta':{'workbook':str(path),'filename':path.name,'savedAt':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),'refreshedAt':datetime.now(timezone.utc).isoformat(),'sheets':list(tables),'formulaErrors':len(formula_errors),'coverage':{'contacts':len(contacts),'calls':len(calls),'deals':len(deals),'cash':len(cash),'milestones':len(milestones),'market':len(market)},'locationBasis':'Published company country; map markers represent country-level centroids, not verified company coordinates.'}}

if __name__=='__main__':
    model=load_model()
    print(json.dumps({'meta':model['meta'],'issues':model['issues'],'headers':{k:list(v['headers'].values()) for k,v in read_workbook()[1].items()}},indent=2))
