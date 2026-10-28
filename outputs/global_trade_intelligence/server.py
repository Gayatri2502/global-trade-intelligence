from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, os, sys, webbrowser, threading, urllib.request
from workbook_data import load_model, WORKBOOK, ROOT

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
    def do_GET(self):
        route=urlparse(self.path).path
        if route=='/api/data':
            try:body=json.dumps(load_model(),ensure_ascii=False).encode();status=200
            except Exception as exc:body=json.dumps({'error':str(exc)}).encode();status=500
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.end_headers();self.wfile.write(body)
        elif route=='/api/workbook':
            self.send_response(200);self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');self.send_header('Content-Disposition','attachment; filename="Trade_Business_Dashboard.xlsx"');self.end_headers();self.wfile.write(WORKBOOK.read_bytes())
        elif route=='/api/map':
            file=ROOT/'world.geojson'
            if not file.exists():self.send_error(503,'Country boundaries not installed');return
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(file.read_bytes())
        elif route in ['/workbook_data.py','/server.py'] or route.endswith('.command'):
            self.send_error(404)
        else:super().do_GET()

if __name__=='__main__':
    port=int(os.environ.get('TRADE_DASHBOARD_PORT','8765'))
    url=f'http://127.0.0.1:{port}'
    try:
        with urllib.request.urlopen(url+'/api/data',timeout=1) as response:
            existing=json.load(response)
        if existing.get('meta',{}).get('filename')==WORKBOOK.name:
            print('Dashboard already running at '+url,flush=True)
            if '--open' in sys.argv:webbrowser.open(url)
            sys.exit(0)
    except Exception:pass
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print('Global Trade Intelligence — '+url,flush=True)
    print('Workbook: '+str(WORKBOOK),flush=True)
    if '--open' in sys.argv:threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
