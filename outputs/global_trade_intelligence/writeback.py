"""Write approved contact fields to the linked spreadsheet."""
import json
import os
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = 'https://sheets.googleapis.com/v4/spreadsheets/1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0/values'
FIELDS = {'Company': 1, 'Product group': 3, 'Country': 4}
SHEETS = ('Importers', 'Exporters', 'Growers and suppliers')

def send_changes(edits):
    token = os.environ.get('TRADE_SHEETS_ACCESS_TOKEN')
    if not token:
        raise RuntimeError('Google Sheets write access is not configured.')
    if not isinstance(edits, list) or not 1 <= len(edits) <= 100:
        raise ValueError('Send between 1 and 100 edits.')

    def request(range_name, body=None):
        url = BASE + '/' + quote(range_name, safe='')
        if body is not None:
            url += '?valueInputOption=RAW'
        headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
        with urlopen(Request(url, data=body, headers=headers, method='PUT' if body is not None else 'GET'), timeout=15) as response:
            return json.load(response)

    results = []
    for edit in edits:
        try:
            sheet, contact_id, field, before, after = (edit[key] for key in ('sheet', 'id', 'field', 'before', 'after'))
            if sheet not in SHEETS or field not in FIELDS or not contact_id or not all(isinstance(v, str) for v in (contact_id, before, after)) or len(after) > 500 or (field == 'Company' and not after.strip()):
                raise ValueError('Invalid contact edit.')
            prefix = f"'{sheet}'!"
            rows = request(prefix + 'A6:E')['values']
            matches = [(number, row) for number, row in enumerate(rows, 6) if row and row[0] == contact_id]
            if len(matches) != 1:
                raise ValueError('Contact ID is missing or duplicated in the sheet.')
            number, row = matches[0]
            col = FIELDS[field]
            current = str(row[col]) if len(row) > col else ''
            if current != after:
                if current != before:
                    raise ValueError('This cell changed in Google Sheets. Review the current value.')
                request(prefix + f'{chr(65 + col)}{number}', json.dumps({'values': [[after]]}).encode())
            results.append({'ok': True})
        except (KeyError, TypeError, ValueError) as error:
            results.append({'ok': False, 'error': str(error)})
        except OSError:
            results.append({'ok': False, 'error': 'Google Sheets request failed. Verify access and retry.'})
    return results
