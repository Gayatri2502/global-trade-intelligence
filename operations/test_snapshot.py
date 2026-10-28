"""The cloud snapshot adapter must preserve the Excel model's financial semantics."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run import normalize
class SnapshotTest(unittest.TestCase):
 def test_cash_fx_and_dates(self):
  sheets=[dict(name='Cash ledger',values=[[],[],[],[],['Cash ID','Deal ID','Date','Type','Category','Currency','Original amount','FX INR per unit'],['C1','','2026-10-28T00:00:00.000Z','Receipt','Commission receipt','USD',100,84]],formulas=[])]
  model=normalize(dict(sheets=sheets),Path(__file__))
  self.assertEqual(model['cash'][0]['amount'],8400)
  self.assertEqual(model['cash'][0]['date'],'2026-10-28')
 def test_missing_fx_stays_missing(self):
  sheets=[dict(name='Cash ledger',values=[[],[],[],[],['Cash ID','Original amount','FX INR per unit'],['C1',100,'']],formulas=[])]
  model=normalize(dict(sheets=sheets),Path(__file__))
  self.assertIsNone(model['cash'][0]['amount'])
  self.assertTrue(any(i['type']=='Cash amount or FX missing' for i in model['issues']))
if __name__=='__main__':unittest.main()
