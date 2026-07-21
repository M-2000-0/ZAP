import json
import sys
import os
import traceback
from .indexer import ProjectIndex
from .adapters import extract_file, get_adapter
from .analysis import extract_file as extract_zap
from .lexer import Lexer
from .parser import Parser
from .types import TypeChecker


class ZapLSP:
    def __init__(self, root_uri=None):
        self.index = ProjectIndex(root=root_uri or os.getcwd())
        self.index.scan()
        self.capabilities = {
            'textDocumentSync': {
                'openClose': True,
                'change': 1,  # Full document sync
                'diagnostics': True,
            },
            'completionProvider': {
                'triggerCharacters': ['.', ':'],
                'resolveProvider': False,
            },
            'definitionProvider': True,
            'hoverProvider': True,
            'referencesProvider': True,
            'documentSymbolProvider': True,
            'workspaceSymbolProvider': True,
            'diagnosticProvider': {
                'interFileDependencies': False,
                'workspaceDiagnostics': False,
            },
        }
        self._documents = {}
        self._send_notification = None

    def handle_request(self, method, params, msg_id):
        handler = getattr(self, f'handle_{method.replace("/", "_")}', None)
        if handler is None:
            return self._error(msg_id, -32601, f'Method not found: {method}')
        try:
            result = handler(params)
            return self._result(msg_id, result)
        except Exception as e:
            traceback.print_exc()
            return self._error(msg_id, -32603, str(e))

    def handle_initialize(self, params):
        root_uri = params.get('rootUri', '')
        if root_uri:
            root_path = root_uri.replace('file://', '').replace('/', os.sep)
            self.index = ProjectIndex(root=root_path)
            self.index.scan()
        return {
            'capabilities': self.capabilities,
            'serverInfo': {
                'name': 'zap-lsp',
                'version': '0.1',
            },
        }

    def handle_initialized(self, params):
        return None

    def handle_shutdown(self, params):
        return None

    def handle_textDocument_didOpen(self, params):
        doc = params.get('textDocument', {})
        uri = doc.get('uri', '')
        text = doc.get('text', '')
        self._documents[uri] = text
        self._index_document(uri, text)
        self._publish_diagnostics(uri, text)

    def handle_textDocument_didChange(self, params):
        doc = params.get('textDocument', {})
        uri = doc.get('uri', '')
        changes = params.get('contentChanges', [])
        if changes:
            self._documents[uri] = changes[-1].get('text', '')
            self._index_document(uri, self._documents[uri])
            self._publish_diagnostics(uri, self._documents[uri])

    def handle_textDocument_didClose(self, params):
        doc = params.get('textDocument', {})
        uri = doc.get('uri', '')
        self._documents.pop(uri, None)

    def handle_textDocument_definition(self, params):
        uri = params.get('textDocument', {}).get('uri', '')
        position = params.get('position', {})
        line = position.get('line', 0) + 1  # LSP is 0-based
        filepath = self._uri_to_path(uri)
        word = self._word_at_position(uri, position)
        if not word:
            return None
        # Search index for the symbol definition
        results = self.index.query_symbol(word)
        for r in results:
            if r.get('kind') in ('function', 'class', 'assign'):
                def_uri = self._path_to_uri(r.get('file', ''))
                return {
                    'uri': def_uri,
                    'range': {
                        'start': {'line': r.get('line', 1) - 1, 'character': 0},
                        'end': {'line': r.get('line', 1), 'character': 0},
                    },
                }
        return None

    def handle_textDocument_hover(self, params):
        uri = params.get('textDocument', {}).get('uri', '')
        position = params.get('position', {})
        word = self._word_at_position(uri, position)
        if not word:
            return None
        results = self.index.query_symbol(word)
        if results:
            parts = []
            for r in results[:5]:
                kind = r.get('kind', 'symbol')
                scope = r.get('scope', '<global>')
                params_str = ''
                if 'params' in r and r['params']:
                    params_str = f"({', '.join(r['params'])})"
                parts.append(f"**{kind}** `{word}{params_str}`  \nscope: `{scope}`  \nfile: `{os.path.basename(r.get('file', ''))}` L{r.get('line', 0)}")
            return {
                'contents': {
                    'kind': 'markdown',
                    'value': '\n---\n'.join(parts),
                },
            }
        return None

    def handle_textDocument_completion(self, params):
        uri = params.get('textDocument', {}).get('uri', '')
        position = params.get('position', {})
        line = position.get('line', 0) + 1
        col = position.get('character', 0)
        filepath = self._uri_to_path(uri)
        text = self._documents.get(uri, '')
        lines = text.split('\n')
        current_line = lines[position.get('line', 0)] if position.get('line', 0) < len(lines) else ''
        prefix = current_line[:col].strip()
        import_items, local_items = [], []

        if prefix.startswith('import ') or ' from ' in prefix:
            # Suggest import modules
            seen = set()
            for f, idx in self.index.files.items():
                for imp in idx.get('imports', []):
                    mod = imp.get('module', '')
                    if mod and mod not in seen:
                        seen.add(mod)
                        import_items.append({
                            'label': mod,
                            'kind': 9,  # Module
                            'detail': 'module',
                            'insertText': mod,
                        })
            for mod in ('math', 'json', 'os', 'sys', 'random', 'datetime'):
                if mod not in seen:
                    import_items.append({
                        'label': mod,
                        'kind': 9,
                        'detail': 'module (stdlib)',
                        'insertText': mod,
                    })
            return {'isIncomplete': False, 'items': import_items[:20]}

        # Suggest symbols from index
        seen_names = set()
        for f, idx in self.index.files.items():
            for sym in idx.get('symbols', []):
                name = sym.get('name', '')
                if name and name not in seen_names:
                    seen_names.add(name)
                    kind_map = {
                        'function': 3, 'class': 5, 'assign': 6,
                        'method': 2, 'schema': 7, 'service': 7,
                    }
                    local_items.append({
                        'label': name,
                        'kind': kind_map.get(sym.get('kind', ''), 6),
                        'detail': f"{sym.get('kind', 'symbol')} ({sym.get('scope', '<global>')})",
                    })
        local_items.sort(key=lambda x: x['label'])
        return {'isIncomplete': True, 'items': local_items[:100]}

    def handle_textDocument_references(self, params):
        uri = params.get('textDocument', {}).get('uri', '')
        position = params.get('position', {})
        word = self._word_at_position(uri, position)
        if not word:
            return []
        results = self.index.query_symbol(word)
        references = []
        for r in results:
            file_uri = self._path_to_uri(r.get('file', ''))
            references.append({
                'uri': file_uri,
                'range': {
                    'start': {'line': r.get('line', 1) - 1, 'character': 0},
                    'end': {'line': r.get('line', 1), 'character': 0},
                },
            })
        return references

    def handle_textDocument_documentSymbol(self, params):
        uri = params.get('textDocument', {}).get('uri', '')
        filepath = self._uri_to_path(uri)
        idx = self.index.files.get(filepath, {})
        symbols = idx.get('symbols', [])
        result = []
        for sym in symbols:
            kind_map = {
                'function': 12, 'class': 5, 'assign': 13,
                'method': 6, 'schema': 7, 'service': 7,
            }
            result.append({
                'name': sym.get('name', '?'),
                'kind': kind_map.get(sym.get('kind', ''), 13),
                'range': {
                    'start': {'line': sym.get('line', 1) - 1, 'character': 0},
                    'end': {'line': sym.get('line', 1) + 5, 'character': 0},
                },
                'selectionRange': {
                    'start': {'line': sym.get('line', 1) - 1, 'character': 0},
                    'end': {'line': sym.get('line', 1), 'character': 0},
                },
            })
        return result

    def handle_workspace_symbol(self, params):
        query_text = params.get('query', '')
        if not query_text:
            return []
        results = self.index.query_symbol(query_text)
        seen = set()
        items = []
        for r in results:
            name = r.get('name', '')
            if name in seen:
                continue
            seen.add(name)
            kind_map = {
                'function': 12, 'class': 5, 'assign': 13,
                'method': 6, 'schema': 7, 'service': 7,
            }
            items.append({
                'name': name,
                'kind': kind_map.get(r.get('kind', ''), 13),
                'location': {
                    'uri': self._path_to_uri(r.get('file', '')),
                    'range': {
                        'start': {'line': r.get('line', 1) - 1, 'character': 0},
                        'end': {'line': r.get('line', 1), 'character': 0},
                    },
                },
            })
        return items

    # --- diagnostics ---

    def _analyze_document(self, uri, text):
        """Run parser + type checker on a .zap document, return diagnostics."""
        if not text or not uri.endswith('.zap'):
            return []
        try:
            lexer = Lexer(text, uri)
            tokens = lexer.tokenize()
        except Exception as e:
            return [self._make_diagnostic(0, 0, 0, 1, f'Lexer error: {e}', 1)]

        parser = Parser(tokens)
        parser.recovery_mode = True
        try:
            prog = parser.parse()
        except Exception as e:
            return [self._make_diagnostic(0, 0, 0, 1, f'Parse error: {e}', 1)]

        diagnostics = []

        # Parser errors (from recovery mode)
        for err in parser.errors:
            msg = str(err)
            line, col = 0, 0
            if 'L' in msg and ':' in msg:
                try:
                    parts = msg.split(' L')[1].split(':')
                    line = int(parts[0]) - 1
                    col = int(parts[1].split(':')[0])
                except (ValueError, IndexError):
                    pass
            diagnostics.append(self._make_diagnostic(line, col, line, col + 1, msg, 1))

        # Type checker errors
        try:
            tc = TypeChecker()
            tc.check(prog)
            for line, col, msg in tc.errors:
                diagnostics.append(self._make_diagnostic(line - 1, col, line - 1, col + len(msg.split()[-1]) if msg.split() else col + 1, msg, 2))
        except Exception as e:
            diagnostics.append(self._make_diagnostic(0, 0, 0, 1, f'Type check error: {e}', 2))

        return diagnostics

    def _make_diagnostic(self, start_line, start_col, end_line, end_col, message, severity):
        return {
            'range': {
                'start': {'line': start_line, 'character': start_col},
                'end': {'line': end_line, 'character': end_col},
            },
            'severity': severity,  # 1=error, 2=warning, 3=info
            'message': message,
            'source': 'zap-lsp',
        }

    def _publish_diagnostics(self, uri, text):
        """Send diagnostics notification to the client."""
        diagnostics = self._analyze_document(uri, text)
        if self._send_notification:
            self._send_notification('textDocument/publishDiagnostics', {
                'uri': uri,
                'diagnostics': diagnostics,
            })

    # --- helpers ---

    def _index_document(self, uri, text):
        filepath = self._uri_to_path(uri)
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == '.zap':
                # For in-memory .zap files, use a write+index approach
                if not os.path.exists(filepath):
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, 'w') as f:
                        f.write(text)
                idx = extract_zap(filepath)
            else:
                adapter = get_adapter(filepath)
                if adapter and hasattr(adapter, 'extract_source'):
                    idx = adapter.extract_source(text, filepath)
                else:
                    idx = extract_file(filepath)
            if idx:
                self.index.files[filepath] = idx
        except Exception:
            pass

    def _word_at_position(self, uri, position):
        text = self._documents.get(uri, '')
        if not text:
            return None
        lines = text.split('\n')
        line_idx = position.get('line', 0)
        if line_idx >= len(lines):
            return None
        line = lines[line_idx]
        col = position.get('character', 0)
        if col >= len(line):
            col = len(line) - 1
        if col < 0:
            return None
        start = col
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == '_'):
            start -= 1
        end = col
        while end < len(line) and (line[end].isalnum() or line[end] == '_'):
            end += 1
        if start >= end:
            return None
        return line[start:end]

    def _uri_to_path(self, uri):
        path = uri.replace('file://', '').replace('/', os.sep)
        if path.startswith(os.sep) and len(path) > 2 and path[1] == ':':
            pass
        return path

    def _path_to_uri(self, path):
        return 'file://' + path.replace(os.sep, '/')

    def _result(self, msg_id, result):
        return {'jsonrpc': '2.0', 'id': msg_id, 'result': result}

    def _error(self, msg_id, code, message):
        return {'jsonrpc': '2.0', 'id': msg_id, 'error': {'code': code, 'message': message}}


def _send_notification(lsp, method, params):
    """Send a notification (no id) to the client."""
    msg = {'jsonrpc': '2.0', 'method': method, 'params': params}
    resp_str = json.dumps(msg)
    sys.stdout.buffer.write(f'Content-Length: {len(resp_str)}\r\n\r\n{resp_str}'.encode())
    sys.stdout.buffer.flush()

def run_lsp():
    """Run the LSP server over stdin/stdout."""
    lsp = ZapLSP()
    lsp._send_notification = lambda m, p: _send_notification(lsp, m, p)
    import sys
    stdin = sys.stdin.buffer
    while True:
        try:
            # Read headers one line at a time
            content_length = 0
            while True:
                line = stdin.readline()
                if not line:
                    return  # EOF
                line_str = line.decode('utf-8').strip()
                if not line_str:
                    break  # End of headers
                if line_str.lower().startswith('content-length:'):
                    content_length = int(line_str.split(':')[1].strip())

            if content_length == 0:
                continue

            # Read exact body
            body = stdin.read(content_length).decode('utf-8')
            msg = json.loads(body)
            msg_id = msg.get('id')
            method = msg.get('method', '')
            params = msg.get('params', {})

            response = lsp.handle_request(method, params, msg_id)
            if response is not None:
                resp_str = json.dumps(response)
                sys.stdout.buffer.write(f'Content-Length: {len(resp_str)}\r\n\r\n{resp_str}'.encode())
                sys.stdout.buffer.flush()
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            traceback.print_exc()
