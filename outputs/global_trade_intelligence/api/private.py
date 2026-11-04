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
<body class="login-page"><section class="login-card"><p class="eyebrow">TRADE LEDGER</p>
<h1>Sign in to Trade Ledger</h1><p>Use the approved Google account to access your trading workspace.</p>
<a class="login-button" href="/auth/login">Sign in with Google</a></section></body></html>"""
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
                return self.reply(403, 'Sign-in could not be verified. Start again from Trade Ledger.', cookie=expired)
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
                    return self.reply(403, 'This Google account does not have access to Trade Ledger.', cookie=expired)
                expiry = str(int(time.time()) + 3600)
                session = expiry + '.' + self.signature(OWNER + ':' + expiry)
                self.send_response(303)
                self.send_header('Location', '/')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Set-Cookie', expired)
                self.send_header('Set-Cookie', self.set_cookie('trade-session', session, 3600))
                self.end_headers()
                return
            except (OSError, KeyError, ValueError):
                return self.reply(502, 'Google sign-in failed. Please try again.', cookie=expired)
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
            return self.reply(403, 'Access denied.')
        return self.write_records(ORIGIN)

    def do_HEAD(self):
        self.reply(405)
