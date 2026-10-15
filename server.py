"""Shelfwise web server. Run it with:  python server.py

It needs nothing beyond Python 3.8+. It serves the website from the web/ folder and a
JSON API under /api that reads and writes the SQLite database (library.db).

    python server.py                 start on http://localhost:8000
    python server.py --port 5000     use another port
    python server.py --reset         rebuild library.db from schema.sql and seed.sql first
"""
import argparse
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import library
from library import LibraryError

ROOT = Path(__file__).parent
WEB = ROOT / 'web'
DB_PATH = ROOT / 'library.db'


def _truthy(value):
    return str(value or '').lower() in ('1', 'true', 'yes')


# Each route: (method, path pattern, function(conn, params, query, body) -> (status, data))
def build_routes():
    L = library
    return [
        ('GET',    r'^/api/health$',                  lambda c, p, q, b: (200, {'ok': True})),
        ('GET',    r'^/api/config$',                  lambda c, p, q, b: (200, L.config())),
        ('GET',    r'^/api/stats$',                   lambda c, p, q, b: (200, L.stats(c))),
        ('GET',    r'^/api/books$',                   lambda c, p, q, b: (200, L.list_books(c, q.get('q', ''), q.get('category', ''), _truthy(q.get('available'))))),
        ('POST',   r'^/api/books$',                   lambda c, p, q, b: (201, L.add_book(c, b))),
        ('PUT',    r'^/api/books/(\d+)$',             lambda c, p, q, b: (200, L.update_book(c, int(p[0]), b))),
        ('DELETE', r'^/api/books/(\d+)$',             lambda c, p, q, b: (200, L.delete_book(c, int(p[0])) or {'deleted': True})),
        ('GET',    r'^/api/members$',                 lambda c, p, q, b: (200, L.list_members(c, q.get('q', '')))),
        ('POST',   r'^/api/members$',                 lambda c, p, q, b: (201, L.add_member(c, b))),
        ('PUT',    r'^/api/members/(\d+)$',           lambda c, p, q, b: (200, L.update_member(c, int(p[0]), b))),
        ('GET',    r'^/api/loans$',                   lambda c, p, q, b: (200, L.list_loans(c, q.get('status', 'all'), int(q['member_id']) if q.get('member_id', '').isdigit() else None))),
        ('POST',   r'^/api/loans$',                   lambda c, p, q, b: (201, _borrow(c, b))),
        ('POST',   r'^/api/loans/(\d+)/return$',      lambda c, p, q, b: (200, L.return_loan(c, int(p[0])))),
        ('POST',   r'^/api/loans/(\d+)/pay$',         lambda c, p, q, b: (200, L.pay_fine(c, int(p[0])))),
    ]


def _borrow(conn, body):
    try:
        return library.borrow(conn, int(body.get('book_id')), int(body.get('member_id')))
    except (TypeError, ValueError):
        raise LibraryError('Choose a book and a member.')


class Handler(BaseHTTPRequestHandler):
    routes = build_routes()
    server_version = 'Shelfwise'

    # ----- helpers -----
    def _send(self, status, payload, content_type='application/json; charset=utf-8'):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store' if content_type.startswith('application/json') else 'no-cache')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get('Content-Length') or 0)
        if length > 100_000:
            raise LibraryError('Request is too large.', 413)
        if not length:
            return {}
        try:
            data = json.loads(self.rfile.read(length))
        except ValueError:
            raise LibraryError('The request body is not valid JSON.')
        if not isinstance(data, dict):
            raise LibraryError('The request body must be a JSON object.')
        return data

    # ----- routing -----
    def _api(self, method, path, query):
        for route_method, pattern, handler in self.routes:
            match = re.match(pattern, path)
            if match and route_method == method:
                conn = library.connect(DB_PATH)
                try:
                    body = self._body() if method in ('POST', 'PUT') else {}
                    status, data = handler(conn, match.groups(), query, body)
                    return self._send(status, data)
                except LibraryError as err:
                    return self._send(err.status, {'error': str(err)})
                finally:
                    conn.close()
        if any(re.match(pattern, path) for _, pattern, _ in self.routes):
            return self._send(405, {'error': 'Method not allowed.'})
        return self._send(404, {'error': 'Not found.'})

    def _static(self, path):
        relative = unquote(path).lstrip('/') or 'index.html'
        target = (WEB / relative).resolve()
        if WEB.resolve() not in target.parents and target != WEB.resolve():
            return self._send(403, {'error': 'Forbidden.'})
        if target.is_dir():
            target = target / 'index.html'
        if not target.is_file():
            return self._send(404, b'Not found', 'text/plain; charset=utf-8')
        kind = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        if kind.startswith('text/') or kind in ('application/javascript', 'application/json'):
            kind += '; charset=utf-8'
        return self._send(200, target.read_bytes(), kind)

    def _handle(self, method):
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            if parsed.path.startswith('/api/'):
                return self._api(method, parsed.path.rstrip('/') or '/', query)
            if method in ('GET', 'HEAD'):
                return self._static(parsed.path)
            return self._send(405, {'error': 'Method not allowed.'})
        except LibraryError as err:
            return self._send(err.status, {'error': str(err)})
        except Exception as err:  # never leak internals to the browser
            self.log_error('Unexpected error: %r', err)
            return self._send(500, {'error': 'Something went wrong on the server.'})

    def do_GET(self):    self._handle('GET')
    def do_HEAD(self):   self._handle('HEAD')
    def do_POST(self):   self._handle('POST')
    def do_PUT(self):    self._handle('PUT')
    def do_DELETE(self): self._handle('DELETE')

    def log_message(self, fmt, *args):
        if '/api/' in (self.path or ''):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description='Shelfwise library management server')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--reset', action='store_true', help='rebuild the database from schema.sql and seed.sql')
    args = parser.parse_args()

    library.init_db(DB_PATH, reset=args.reset)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Shelfwise is running at http://{args.host}:{args.port}  (press Ctrl+C to stop)')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
