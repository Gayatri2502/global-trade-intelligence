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
<section class="trade-illustration" aria-labelledby="login-title">
<div class="login-brand"><span class="login-mark" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M5 10l11-6 11 6v12l-11 6-11-6z M5 10l11 6 11-6 M16 16v12 M10 7l11 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg></span> TRADE LEDGER</div>
<h1 id="login-title">India&#8217;s Global Trade Desk</h1>
<p>Manage trading partners, shipments, and payments for your import and export business.</p>
<div class="login-entry"><a class="login-button" href="/auth/login">Sign in with Google</a><p id="login-status" role="status">Access is limited to the approved account.</p></div>
<svg class="login-routes" viewBox="0 0 580 230" role="img" aria-label="Illustration of cargo imports into India and exports from India">
<defs>
<pattern id="trade-grid" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M22 0H0V22" fill="none" stroke="#29455b" stroke-width=".6"/></pattern>
<marker id="in-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0l10 5-10 5z" fill="#ffba72"/></marker>
<marker id="out-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0l10 5-10 5z" fill="#68e8cd"/></marker>
</defs>
<rect width="580" height="230" rx="16" fill="#0b1628"/><rect width="580" height="230" rx="16" fill="url(#trade-grid)"/>
<g fill="#182943" stroke="#334b68"><path d="M28 64l47-28 69 2 50 21-32 27-34 5-26 38-25-24-35-11zM128 130l39 8 30 27-21 39-26 12-15-44z"/><path d="M229 54l36-24 39 17 42-20 110 13 59 38-26 33-44 11-23 24-33-18-31 8-34-37-44 8-42-29zM250 106l50 5 37 32-28 48-26 17-25-47zM447 168l45-15 44 23-9 29-60 7-26-16z"/></g>
<g fill="none" stroke-width="2.4">
<path class="trade-route" d="M100 85Q198 20 365 117" stroke="#ffba72" marker-end="url(#in-arrow)"/>
<path class="trade-route" d="M481 174Q433 200 380 132" stroke="#ffba72" marker-end="url(#in-arrow)"/>
<path class="trade-route" d="M367 114Q323 36 272 66" stroke="#68e8cd" marker-end="url(#out-arrow)"/>
<path class="trade-route" d="M367 134Q327 198 295 161" stroke="#68e8cd" marker-end="url(#out-arrow)"/>
<path class="trade-route" d="M384 119Q442 54 478 87" stroke="#68e8cd" marker-end="url(#out-arrow)"/>
</g>
<g fill="#b9a5ff"><circle cx="100" cy="85" r="4"/><circle cx="481" cy="174" r="4"/><circle cx="272" cy="66" r="4"/><circle cx="295" cy="161" r="4"/><circle cx="478" cy="87" r="4"/></g>
<circle cx="375" cy="125" r="17" fill="#ffba72" opacity=".18"/><circle cx="375" cy="125" r="8" fill="#ffba72" stroke="#fff0c8" stroke-width="2"/>
<g fill="#dce7f5" font-size="12" font-family="system-ui" text-anchor="middle"><text x="100" y="105">AMERICAS</text><text x="272" y="56">EUROPE</text><text x="283" y="180">AFRICA</text><text x="480" y="74">EAST ASIA</text><text x="490" y="196">OCEANIA</text><text x="397" y="146" fill="#ffe0aa" font-weight="700">INDIA</text></g>
<g transform="translate(85 158)" stroke="#b9a5ff" stroke-width="1.4" fill="none"><path d="M0 13h45l-7 9H7z M9 13V4h12v9 M21 13V4h12v9 M34 13V0h6v13 M1 27q5 3 10 0t10 0 10 0 10 0"/></g>
</svg>
<div class="trade-legend"><span class="trade-import">Imports into India</span><span class="trade-export">Exports from India</span></div>
<small>Illustrative routes</small>
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
        if request.path not in ('/api/ledger', '/api/crawler'):
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
