"""Server-side client for the signed Trade Ledger API."""
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

URL = 'https://cdnzpncsbxavakbvtgem.supabase.co/rest/v1/rpc/trade_ledger'
PUBLISHABLE_KEY = 'sb_publishable_j3HSf2k6MVooEUqvfpHYvQ_g5EHYTEv'

def ledger_request(action, **fields):
    secret = os.getenv('TRADE_SIGNING_SECRET')
    if not secret:
        path = Path(__file__).resolve().parents[2] / 'backend' / '.env'
        for line in path.read_text().splitlines():
            if line.startswith('TRADE_SIGNING_SECRET='):
                secret = line.partition('=')[2].strip().strip('"').strip("'")
                break
    if not secret:
        raise RuntimeError('Workbook signing key is unavailable.')
    body = json.dumps(dict(action=action, **fields), separators=(',', ':'))
    timestamp = int(time.time())
    signature = hmac.new(secret.encode(), f'{timestamp}.{body}'.encode(), hashlib.sha256).hexdigest()
    payload = json.dumps(dict(p_body=body, p_timestamp=timestamp, p_signature=signature)).encode()
    request = Request(URL, data=payload, headers={'apikey': PUBLISHABLE_KEY, 'Content-Type': 'application/json'})
    with urlopen(request, timeout=15) as response:
        return json.load(response)
