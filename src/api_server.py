import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .analysis import extract_file, build_dependency_graph
from .indexer import ProjectIndex
from .protocol import apply_edit, verify_edit, ai_query
from .context import get_context
from .diff import generate_diff
from .tracer import get_tracer

class ZapAPIHandler(BaseHTTPRequestHandler):
    index = None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        params = parse_qs(parsed.query)

        if path == '/health':
            self._json({'status': 'ok'})

        elif path == '/symbols':
            name = params.get('name', [None])[0]
            if name:
                results = self.index.query_symbol(name)
                self._json({'symbol': name, 'results': results})
            else:
                all_syms = {}
                for f, idx in self.index.files.items():
                    all_syms[f] = idx.get('symbols', [])
                self._json({'symbols': all_syms})

        elif path == '/calls':
            name = params.get('name', [None])[0]
            direction = params.get('direction', ['to'])[0]
            if name:
                if direction == 'to':
                    results = self.index.query_calls_to(name)
                else:
                    results = self.index.query_calls_from(f'<global>.{name}')
                self._json({'calls': results, 'name': name, 'direction': direction})
            else:
                all_calls = {}
                for f, idx in self.index.files.items():
                    all_calls[f] = idx.get('calls', [])
                self._json({'calls': all_calls})

        elif path == '/deps':
            graph = self.index.dep_graph
            self._json({'dependency_graph': graph})

        elif path == '/files':
            files = list(self.index.files.keys())
            self._json({'files': files})

        elif path == '/file':
            filepath = params.get('path', [None])[0]
            if filepath and os.path.exists(filepath):
                with open(filepath) as f:
                    content = f.read()
                idx_data = self.index.files.get(filepath, {})
                self._json({
                    'file': filepath,
                    'content': content,
                    'symbols': idx_data.get('symbols', []),
                    'calls': idx_data.get('calls', []),
                })
            else:
                self._json({'error': 'file not found'}, 404)

        elif path == '/context':
            ctx = get_context()
            self._json({'context': ctx.data})

        elif path == '/query':
            query_text = params.get('q', [None])[0]
            if query_text:
                results = ai_query(query_text)
                self._json({'query': query_text, 'results': results})
            else:
                self._json({'error': '?q= parameter required'}, 400)

        elif path == '/diff':
            filepath = params.get('path', [None])[0]
            if filepath and os.path.exists(filepath):
                with open(filepath) as f:
                    lines = f.readlines()
                self._json({
                    'file': filepath,
                    'lines': len(lines),
                    'preview': lines[:50],
                })
            else:
                self._json({'error': 'file not found'}, 404)

        elif path == '/traces':
            tracer = get_tracer()
            type_filter = params.get('type', [None])[0]
            limit = int(params.get('limit', ['100'])[0])
            offset = int(params.get('offset', ['0'])[0])
            if type_filter:
                events = tracer.events(type_=type_filter, limit=limit, offset=offset)
            else:
                events = tracer.events(limit=limit, offset=offset)
            self._json({
                'traces': events,
                'total': len(tracer._events),
                'stats': tracer.stats(),
            })

        elif path == '/traces/errors':
            tracer = get_tracer()
            self._json({'errors': tracer.errors(limit=50)})

        elif path == '/traces/slow':
            tracer = get_tracer()
            threshold = float(params.get('threshold', ['0.1'])[0])
            self._json({
                'slow_calls': tracer.slow_calls(threshold=threshold),
                'threshold': threshold,
            })

        elif path == '/traces/stats':
            tracer = get_tracer()
            self._json(tracer.stats())

        else:
            self._json({'error': 'not found', 'paths': [
                '/health', '/symbols', '/calls', '/deps', '/files',
                '/file?path=', '/context', '/query?q=', '/diff?path=',
                '/traces', '/traces/errors', '/traces/slow', '/traces/stats',
            ]}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode() if length else '{}'
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json({'error': 'invalid JSON'}, 400)
            return

        if path == '/edit':
            filepath = data.get('file')
            edit = data.get('edit')
            if not filepath or not edit:
                self._json({'error': 'file and edit required'}, 400)
                return
            if data.get('verify_only'):
                result = verify_edit(edit, filepath)
                self._json(result)
            else:
                result = apply_edit(edit, filepath)
                if result.get('applied'):
                    self.index._index_file(filepath, self.index.files)
                    self.index.dep_graph = build_dependency_graph(
                        list(self.index.files.values()))
                self._json(result)

        elif path == '/reindex':
            self.index.scan()
            self.index.save()
            self._json({'status': 'reindexed', 'files': len(self.index.files)})

        elif path == '/traces/clear':
            get_tracer().clear()
            self._json({'status': 'traces cleared'})

        elif path == '/traces/toggle':
            tracer = get_tracer()
            action = data.get('enabled')
            if action is True:
                tracer.enable()
            elif action is False:
                tracer.disable()
            self._json({'enabled': tracer.enabled})

        elif path == '/context':
            ctx = get_context()
            for key, value in data.items():
                ctx.set(key, value)
            ctx.save()
            self._json({'status': 'updated', 'keys': list(data.keys())})

        else:
            self._json({'error': 'not found'}, 404)

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())

    def log_message(self, format, *args):
        sys.stderr.write(f"[zap api] {args[0]} {args[1]} {args[2]}\n")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def serve(port=8732, host='127.0.0.1'):
    ZapAPIHandler.index = ProjectIndex()
    ZapAPIHandler.index.scan()
    ZapAPIHandler.index.save()
    print(f"[zap api] starting on http://{host}:{port}")
    print(f"[zap api] {len(ZapAPIHandler.index.files)} files indexed")
    server = HTTPServer((host, port), ZapAPIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[zap api] stopped")
        server.server_close()
