"""Parse contact files for a preview or a database import."""
import base64
import csv
import io
import uuid
import zipfile

def parse_contacts(payload):
    content = base64.b64decode(payload['content'], validate=True)
    if payload['name'].lower().endswith('.xlsx'):
        from openpyxl import load_workbook
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 30_000_000:
                raise ValueError('Workbook is too large.')
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try:
            return parse_rows(workbook.active.values)
        finally:
            workbook.close()
    if not payload['name'].lower().endswith('.csv'):
        raise ValueError('Choose a CSV or XLSX file.')
    return parse_rows(csv.reader(io.StringIO(content.decode('utf-8-sig'))))

def parse_rows(rows):
    rows = iter(rows)
    headers = []
    for _, row in zip(range(10), rows):
        headers = [str(cell or '').strip().lower() for cell in row]
        if 'company' in headers or 'name' in headers:
            break
    else:
        raise ValueError('Add a Company or Name column.')
    records, errors = [], []
    for index, row in enumerate(rows, 1):
        if index > 500:
            raise ValueError('Use at most 500 rows per file.')
        if not any(row):
            continue
        data = dict(zip(headers, (str(cell or '').strip() for cell in row)))
        name = data.get('company') or data.get('name')
        if not name:
            errors.append(f'Data row {index}: missing company.')
            continue
        role = data.get('role') or data.get('business role') or 'Buyer'
        role = 'Exporter' if role.lower().startswith('export') else 'Grower / supplier' if role.lower().startswith(('grower', 'supplier')) else 'Buyer'
        records.append(dict(id='TL-'+str(uuid.uuid4()), name=name, role=role,
                            country=data.get('country', ''), product=data.get('product group', data.get('product','')),
                            email=data.get('email',''), phone=data.get('phone',''),
                            source=data.get('website / source url',data.get('website','')),
                            stage='New', priority='Unassessed', verified=False, ratings={}))
    return records, errors
