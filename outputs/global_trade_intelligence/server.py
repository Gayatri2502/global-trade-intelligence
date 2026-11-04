from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, os, sys, webbrowser, threading, urllib.request
import urllib.error
from ledger_client import ledger_request
from bulk_contacts import parse_contacts

ROOT = Path(__file__).resolve().parent

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
    def do_POST(self):
        return self.write_records(f'http://127.0.0.1:{self.server.server_port}')

    def write_records(self, origin):
        if self.path not in ('/api/import', '/api/ledger') or self.headers.get('Origin') != origin:
            self.send_error(403)
            return
        if self.path == '/api/import':
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2_000_000:
                    raise ValueError('Upload must be under 1.5 MB.')
                payload = json.loads(self.rfile.read(size))
                records, errors = parse_contacts(payload)
                if payload.get('commit') is True:
                    if errors or not records:
                        raise ValueError('Correct invalid rows before importing.')
                    result = ledger_request('import', records=records)
                else:
                    result = {'records': records, 'errors': errors}
                status = 200
            except (ValueError, KeyError, TypeError) as error:
                status, result = 400, {'error': str(error)}
            except (OSError, RuntimeError, ImportError):
                status, result = 502, {'error': 'Could not process the workbook or reach Supabase.'}
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return
        if self.path == '/api/ledger':
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 64000:
                    raise ValueError('Invalid record size')
                change = json.loads(self.rfile.read(size))
                result = ledger_request('save', **change)
                status = 200
            except urllib.error.HTTPError as error:
                code = json.loads(error.read()).get('code')
                status = 409 if code == '40001' else 502
                result = {'error': 'Record changed. Reload and retry.' if status == 409 else 'Database rejected the record.'}
            except (ValueError, TypeError, OSError, RuntimeError):
                status, result = 400, {'error': 'Unable to save this record.'}
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return
    def do_GET(self):
        route=urlparse(self.path).path
        if route == '/api/ledger':
            try:
                body, status = json.dumps(ledger_request('read')), 200
            except (OSError, RuntimeError):
                body, status = json.dumps({'error': 'Private database unavailable.'}), 502
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body.encode())
        elif route=='/api/map':
            file=ROOT/'world.geojson'
            if not file.exists():self.send_error(503,'Country boundaries not installed');return
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(file.read_bytes())
        elif route not in ('/', '/index.html', '/app.js', '/metrics.mjs', '/style.css', '/world.geojson'):
            self.send_error(404)
        else:super().do_GET()

if __name__=='__main__':
    port=int(os.environ.get('TRADE_DASHBOARD_PORT','8765'))
    url=f'http://127.0.0.1:{port}'
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print('Global Trade Intelligence — '+url,flush=True)
    if '--open' in sys.argv:threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
