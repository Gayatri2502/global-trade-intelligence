"""Vercel entry point. All ledger operations require a verified Google session."""
from pathlib import Path
from http.cookies import SimpleCookie, CookieError
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from server import Handler

ORIGIN = 'https://trade-ledger-seven.vercel.app'
CALLBACK = ORIGIN + '/auth/callback'
OWNER = 'alphacentauric.ai@gmail.com'


class handler(Handler):
    def reply(self, status, message='', location=None, cookie=None):
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Referrer-Policy', 'no-referrer')
        if location:
            self.send_header('Location', location)
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(message.encode())

    def cookie(self, name):
        try:
            value = SimpleCookie(self.headers.get('Cookie', '')).get('__Host-' + name)
            return value.value if value else ''
        except CookieError:
            return ''

    def set_cookie(self, name, value, age):
        return f'__Host-{name}={value}; Path=/; Max-Age={age}; Secure; HttpOnly; SameSite=Lax'

    def signature(self, value):
        return hmac.new(os.environ['TRADE_SESSION_SECRET'].encode(), value.encode(), hashlib.sha256).hexdigest()

    def signed_in(self):
        if not os.getenv('TRADE_SESSION_SECRET'):
            return False
        expiry, _, signature = self.cookie('trade-session').partition('.')
        return (expiry.isascii() and expiry.isdecimal() and len(expiry) <= 12
                and int(expiry) > time.time() and signature.isascii()
                and hmac.compare_digest(signature, self.signature(OWNER + ':' + expiry)))

    def do_GET(self):
        request = urlsplit(self.path)
        if request.path in ('/', '/index.html', '/login'):
            if request.path != '/login' and not self.signed_in():
                return self.reply(303, location='/login')
            if request.path == '/login':
                if self.signed_in():
                    return self.reply(303, location='/')
                body = b"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in | Trade Ledger</title><link rel="stylesheet" href="/style.css">
<body class="login-page"><main class="login-layout">
<section class="trade-illustration" aria-label="Illustration of international shipping routes">
<p class="eyebrow">GLOBAL TRADE WORKSPACE</p><h1>Trade across borders</h1>
<p>Trade Ledger is the Global Trade Works workspace for importers and exporters. Find trading partners, assess leads, and follow a deal from the first call through shipment and payment.</p>
<div class="login-entry"><a class="login-button" href="/auth/login">Sign in with Google</a><p id="login-status" role="status">Access is limited to the approved account.</p></div>
<svg viewBox="0 0 580 330" role="img" aria-label="Illustrative routes linking the Americas, Europe, Africa, and Asia">
<defs><pattern id="trade-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#29455b" stroke-width=".55"/></pattern></defs>
<rect width="580" height="330" rx="16" fill="url(#trade-grid)"/>
<g fill="#173147" stroke="#31566e" stroke-width="1.5">
<path d="M50 78l32-34 66 2 48 27-30 29-13 32-29 3-9 32-26-20-16-39z"/>
<path d="M135 173l46 5 35 38-26 57-26 34-10-49-18-33z"/>
<path d="M251 80l39-31 33 18 35-25 111 5 67 44-28 29-38 12-27 48-46-27-26 14-32-46-28 8-37-15z"/>
<path d="M270 130l53 2 37 35-29 67-23 22-20-52-21-34z"/>
<path d="M450 230l32-20 48 14 14 31-26 24-57-7z"/>
</g>
<g fill="none" stroke="#70e6d5" stroke-width="2">
<path class="trade-route" d="M106 110Q181 19 286 97"/>
<path class="trade-route" d="M286 97Q362 49 426 137"/>
<path class="trade-route" d="M426 137Q475 146 489 248"/>
<path class="trade-route" d="M178 223Q251 151 312 192"/>
<path class="trade-route" d="M312 192Q374 198 426 137"/>
</g>
<g fill="#93f6e7" stroke="#173147" stroke-width="3"><circle cx="106" cy="110" r="6"/><circle cx="286" cy="97" r="6"/><circle cx="426" cy="137" r="6"/><circle cx="489" cy="248" r="6"/><circle cx="178" cy="223" r="6"/><circle cx="312" cy="192" r="6"/></g>
<g fill="#a6bdce" font-size="11" font-family="system-ui"><text x="66" y="129">N. AMERICA</text><text x="253" y="119">EUROPE</text><text x="436" y="140">ASIA</text><text x="458" y="292">OCEANIA</text><text x="121" y="209">S. AMERICA</text><text x="279" y="179">AFRICA</text></g>
</svg><small>Illustrative connections between sourcing and destination markets.</small></section>
<section class="workspace-preview" aria-label="What is inside Trade Ledger">
<p class="eyebrow">INSIDE THE WORKSPACE</p><h2>From a new lead to a settled deal</h2>
<div class="preview-steps"><article><span>01</span><h3>Find trading partners</h3><p>Browse importer and exporter directories, compare markets, and review source evidence.</p></article>
<article><span>02</span><h3>Build your pipeline</h3><p>Score contacts, log calls, schedule follow-ups, and track quotes and deals.</p></article>
<article><span>03</span><h3>Follow execution and cash</h3><p>Track shipment milestones, compliance checks, receipts, and commission.</p></article></div>
</section></main><script type="module" src="/login.mjs"></script></body></html>"""
            else:
                body = (Path(__file__).resolve().parents[1] / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)
            return
        if request.path == '/auth/login':
            if not all(os.getenv(name) for name in ('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'TRADE_SESSION_SECRET')):
                return self.reply(503, 'Google sign-in setup is pending.')
            state = secrets.token_urlsafe(32)
            params = urlencode(dict(client_id=os.environ['GOOGLE_CLIENT_ID'], redirect_uri=CALLBACK,
                                    response_type='code', scope='openid email', state=state,
                                    login_hint=OWNER, prompt='select_account'))
            return self.reply(302, location='https://accounts.google.com/o/oauth2/v2/auth?' + params,
                              cookie=self.set_cookie('trade-state', state, 600))
        if request.path == '/auth/callback':
            query = parse_qs(request.query)
            state = query.get('state', [''])[0]
            code = query.get('code', [''])[0]
            expired = self.set_cookie('trade-state', '', 0)
            if not code or not state.isascii() or not state or not hmac.compare_digest(state, self.cookie('trade-state')):
                return self.reply(303, location='/login?status='+('cancelled' if query.get('error')==['access_denied'] else 'failed'), cookie=expired)
            try:
                form = urlencode(dict(code=code, client_id=os.environ['GOOGLE_CLIENT_ID'],
                                     client_secret=os.environ['GOOGLE_CLIENT_SECRET'], redirect_uri=CALLBACK,
                                     grant_type='authorization_code')).encode()
                with urlopen(Request('https://oauth2.googleapis.com/token', data=form), timeout=10) as response:
                    token = json.load(response)['access_token']
                profile = Request('https://openidconnect.googleapis.com/v1/userinfo',
                                  headers={'Authorization': 'Bearer ' + token})
                with urlopen(profile, timeout=10) as response:
                    identity = json.load(response)
                if identity.get('email_verified') is not True or identity.get('email', '').lower() != OWNER:
                    return self.reply(303, location='/login?status=denied', cookie=expired)
                expiry = str(int(time.time()) + 3600)
                session = expiry + '.' + self.signature(OWNER + ':' + expiry)
                self.send_response(303)
                self.send_header('Location', '/?signed-in=1')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Set-Cookie', expired)
                self.send_header('Set-Cookie', self.set_cookie('trade-session', session, 3600))
                self.end_headers()
                return
            except (OSError, KeyError, ValueError):
                return self.reply(303, location='/login?status=failed', cookie=expired)
        if request.path != '/api/ledger':
            return self.reply(404)
        if not self.signed_in():
            return self.reply(401, 'Sign in with the approved Google account.')
        return super().do_GET()

    def do_POST(self):
        if self.headers.get('Origin') != ORIGIN:
            return self.reply(403, 'Access denied.')
        if urlsplit(self.path).path == '/auth/logout':
            return self.reply(303, location='/login', cookie=self.set_cookie('trade-session', '', 0))
        if not self.signed_in():
            return self.reply(401, 'Sign in with the approved Google account.')
        return self.write_records(ORIGIN)

    def do_HEAD(self):
        self.reply(405)
