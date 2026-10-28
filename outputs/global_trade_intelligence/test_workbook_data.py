"""Synthetic in-memory fixtures only. Never writes a workbook or operational record."""
from unittest.mock import patch
from workbook_data import load_model, WORKBOOK

contacts=[{'_row':6,'_sheet':'Importers','Contact ID':'SYNTHETIC-C1','Company':'Synthetic test buyer','Product group':'Moringa','Country':'India','Phone':'+911234567890'}]
deal={'_row':6,'Deal ID':'SYNTHETIC-D1','Contact ID':'SYNTHETIC-C1','Supplier Contact ID':None,'Trade direction':'Export','Product':'Moringa','Origin country':'India','Destination country':'United Kingdom','Stage':'Invoiced','Invoice date':'2026-02-03','Invoice net amount original currency':10000,'FX to INR':1,'Invoice due date':'2026-03-03','Contract commission original':2000,'Commission FX to INR':1,'Commission earned date':'2026-02-03'}
costs=['Product cost INR','Packing / processing INR','Origin inland / handling INR','Testing / export documents INR','Insurance INR','International freight INR','Duty / nonrecoverable tax INR','Destination broker / handling INR','Final mile / storage INR','Bank / payment fees INR','Other direct costs INR']
deal.update(dict(zip(costs,[4000,300,200,100,0,500,0,100,200,50,50])))
def event(i,kind,category,amount):return{'_row':6+i,'Cash ID':'SYNTHETIC-X'+str(i),'Deal ID':'SYNTHETIC-D1','Date':'2026-02-05','Type':kind,'Category':category,'Original amount':amount,'FX INR per unit':1,'Currency':'INR'}
events=[event(1,'Receipt','Customer receipt',6000),event(2,'Receipt','Commission receipt',500),event(3,'Payment','Customer refund',1000),event(4,'Payment','Commission refund',100)]
tables={'Importers':contacts,'Exporters':[],'Growers and suppliers':[],'Deals':[deal],'Cash ledger':events}
with patch('workbook_data.read_workbook',return_value=(tables,{},[])):
    model=load_model(WORKBOOK)
    d=model['deals'][0]
    assert d['revenue']==10000 and d['directCost']==5500 and d['contribution']==4500
    assert d['receipts']==5000 and d['receivable']==5000
    assert d['commissionExpected']==2000 and d['commissionEarned']==2000
    assert d['commissionReceived']==400 and d['commissionOutstanding']==1600
events[0]['FX INR per unit']=None
with patch('workbook_data.read_workbook',return_value=(tables,{},[])):
    model=load_model(WORKBOOK)
    assert model['deals'][0]['receipts'] is None
    assert model['deals'][0]['receivable'] is None
    assert any(i['type']=='Cash amount or FX missing' for i in model['issues'])
print('PASS: XLSX normalization, full direct costs, net customer refunds, net commission refunds, expected vs earned commission and incomplete FX. No source file was changed.')
