import sys
import os
import json
from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator

_global_evaluator = None

def get_evaluator():
    global _global_evaluator
    if _global_evaluator is None:
        _global_evaluator = Evaluator()
    return _global_evaluator

def run_source(source, filename='<stdin>', new_env=False):
    lexer = Lexer(source, filename)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    if new_env:
        evaluator = Evaluator()
        return evaluator.evaluate(ast)
    evaluator = get_evaluator()
    return evaluator.evaluate(ast)

def run_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    return run_source(source, path, new_env=True)

def repl():
    global _global_evaluator
    _global_evaluator = Evaluator()
    print("Zap v0.1 - AI-native programming language")
    print("Type 'exit' or Ctrl+C to quit")
    print()
    source_lines = []
    while True:
        try:
            prompt = "... " if source_lines else "zap> "
            line = input(prompt)
            if line.strip() == 'exit':
                break
            source_lines.append(line)
            if line.strip() == '' or line.rstrip().endswith(':'):
                continue
            source = '\n'.join(source_lines)
            try:
                result = run_source(source)
                if result is not None:
                    print(result)
            except (SyntaxError, NameError, RuntimeError, ZeroDivisionError, TypeError, ValueError) as e:
                print(f"Error: {e}")
            source_lines = []
        except (KeyboardInterrupt, EOFError):
            print()
            break

def cmd_deps(args):
    from src.analysis import extract_file, build_dependency_graph, format_graph
    files = [f for f in args if f.endswith('.zap') and os.path.exists(f)]
    if not files:
        files = []
        for dirpath, _, filenames in os.walk('.'):
            for fn in filenames:
                if fn.endswith('.zap'):
                    files.append(os.path.join(dirpath, fn))
    indexes = [extract_file(f) for f in files]
    graph = build_dependency_graph(indexes)
    if '--dot' in args:
        print(format_graph(graph))
    else:
        print(json.dumps(graph, indent=2))

def cmd_symbols(args):
    from src.analysis import extract_file
    for f in args:
        if not os.path.exists(f):
            continue
        idx = extract_file(f)
        print(f"=== {f} ===")
        for sym in idx['symbols']:
            print(f"  {sym['kind']:8} {sym['scope']}.{sym['name']} (line {sym['line']})")
        for c in idx['calls']:
            print(f"  call     {c['from_scope']} -> {c['callee']} (line {c['line']})")
        if idx['imports']:
            for imp in idx['imports']:
                print(f"  import   {imp}")

def cmd_index(args):
    from src.indexer import ProjectIndex
    idx = ProjectIndex()
    idx.scan()
    idx.save()
    print(f"indexed {len(idx.files)} files -> .zapindex")

def cmd_watch(args):
    from src.indexer import ProjectIndex
    interval = 2.0
    for a in args:
        if a.startswith('--interval='):
            try:
                interval = float(a.split('=')[1])
            except ValueError:
                pass
    idx = ProjectIndex()
    print(f"watching for .zap changes (interval={interval}s)...")
    try:
        idx.watch(interval=interval)
    except KeyboardInterrupt:
        print("\nstopped")

def cmd_patch(args):
    from src.diff import apply_patch, PatchError
    if not args:
        print("usage: zap patch <file.zap> '<patch-json>'", file=sys.stderr)
        print("   or: zap patch <file.zap> --file <patch.json>", file=sys.stderr)
        sys.exit(1)
    filepath = args[0]
    patch_json = None
    if '--file' in args:
        fi = args.index('--file')
        if fi + 1 < len(args):
            with open(args[fi + 1]) as f:
                patch_json = f.read()
    else:
        patch_json = sys.stdin.read() if len(args) < 2 else ' '.join(args[1:])
    if not patch_json or not patch_json.strip():
        print("no patch provided", file=sys.stderr)
        sys.exit(1)
    try:
        patch = json.loads(patch_json)
    except json.JSONDecodeError as e:
        print(f"invalid patch JSON: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        result = apply_patch(filepath, patch)
        print(json.dumps(result))
    except (PatchError, IOError) as e:
        print(f"patch error: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_diff(args):
    from src.diff import generate_diff
    if len(args) < 2:
        print("usage: zap diff <file-before.zap> <file-after.zap>", file=sys.stderr)
        sys.exit(1)
    with open(args[0]) as f:
        before = f.read()
    with open(args[1]) as f:
        after = f.read()
    patches = generate_diff(before, after)
    print(json.dumps(patches, indent=2))

def cmd_query(args):
    from src.indexer import ProjectIndex
    if not args:
        print("usage: zap query <symbol-name>", file=sys.stderr)
        sys.exit(1)
    name = args[0]
    idx = ProjectIndex()
    idx.load()
    syms = idx.query_symbol(name)
    calls_to = idx.query_calls_to(name)
    result = {'symbol': name, 'definitions': syms, 'callers': calls_to}
    print(json.dumps(result, indent=2))

def cmd_serve(args):
    from src.api_server import serve
    port = 8732
    host = '127.0.0.1'
    for a in args:
        if a.startswith('--port='):
            try:
                port = int(a.split('=')[1])
            except ValueError:
                pass
        if a.startswith('--host='):
            host = a.split('=')[1]
    serve(port=port, host=host)

def cmd_edit(args):
    from src.protocol import apply_edit, verify_edit
    import json
    if len(args) < 2:
        print("usage: zap edit <file.zap> '<json-edit>' or --file <edit.json>", file=sys.stderr)
        sys.exit(1)
    filepath = args[0]
    edit_json = None
    if '--file' in args:
        fi = args.index('--file')
        with open(args[fi + 1]) as f:
            edit_json = f.read()
    elif '--verify' in args:
        edit_json = ' '.join(a for a in args[1:] if a != '--verify')
        edit = json.loads(edit_json)
        result = verify_edit(edit, filepath)
        print(json.dumps(result, indent=2))
        return
    else:
        edit_json = sys.stdin.read() if len(args) < 2 else ' '.join(args[1:])
    edit = json.loads(edit_json)
    result = apply_edit(edit, filepath)
    print(json.dumps(result, indent=2))

def cmd_scaffold(args):
    from src.codegen import scaffold, generate_crud, generate_app, validate_generated
    desc = ' '.join(args) if args else 'a full-stack app with service and database'
    if desc.startswith('crud:'):
        entity = desc.split(':', 1)[1].strip()
        result = generate_crud(entity)
        parts = [result['schema'], result['model'], result['service']]
        parts.extend(result['apis'])
        parts.append(result['page'])
        source = '\n'.join(parts)
    elif desc.startswith('app:'):
        entities_desc = desc.split(':', 1)[1].strip()
        entities = []
        for ent in entities_desc.split(','):
            ent = ent.strip()
            if ent:
                entities.append({'name': ent, 'fields': [
                    ('id', 'int'), ('name', 'str'), ('created_at', 'str')
                ]})
        source = generate_app(entities)
    else:
        source = scaffold(desc)
    print(f"# Generated for: {desc}")
    print(source)
    result = validate_generated(source)
    print(f"\n# Validation: {result}")

def cmd_model(args):
    from src.codegen import generate_model, generate_schema, generate_api, generate_page, generate_service, generate_database, validate_generated
    import json
    if not args:
        print("usage: zap generate <type> <name> [...options]", file=sys.stderr)
        print("  types: service, schema, model, api, page, database", file=sys.stderr)
        sys.exit(1)
    kind = args[0]
    name = args[1] if len(args) > 1 else 'App'
    if kind == 'service':
        endpoints = args[2:] if len(args) > 2 else ['get_data', 'create']
        source = generate_service(name, endpoints)
    elif kind == 'schema':
        source = generate_schema(name)
    elif kind == 'model':
        source = generate_model(name)
    elif kind == 'api':
        source = generate_api(path=f'/{name.lower()}')
    elif kind == 'page':
        source = generate_page(name)
    elif kind == 'database':
        source = generate_database(name)
    else:
        print(f"unknown type: {kind}", file=sys.stderr)
        sys.exit(1)
    print(source)
    result = validate_generated(source)
    print(f"# {result}")

def cmd_lsp(args):
    from src.lsp import run_lsp
    run_lsp()

def help_text():
    return """Zap v0.1 - AI-native programming language

Commands:
  zap <file.zap>            Run a .zap file
  zap deps [files...]       Show dependency graph (JSON)
  zap deps --dot [files]    Show dependency graph (DOT format)
  zap symbols <files...>    List symbols and calls in files
  zap index                 Scan project -> .zapindex
  zap watch                 Watch for changes, auto-index
  zap query <name>          Look up a symbol across the index
  zap patch <file> <json>   Apply an AST patch
  zap diff <a> <b>          Generate patch between two files
  zap serve                 Start JSON API server (port 8732)
  zap edit <file> <json>    Apply AI edit (with verify)
  zap scaffold <desc>       Generate code from description
  zap generate <type> <n>   Generate a service/schema/model/api/page
  zap lsp                   Start LSP server (stdin/stdout JSON-RPC)
  (no args)                 Start REPL
"""

def main():
    if len(sys.argv) < 2:
        repl()
        return

    cmd = sys.argv[1]
    cmd_args = sys.argv[2:]

    subcommands = {
        'deps': cmd_deps,
        'symbols': cmd_symbols,
        'index': cmd_index,
        'watch': cmd_watch,
        'patch': cmd_patch,
        'diff': cmd_diff,
        'query': cmd_query,
        'serve': cmd_serve,
        'edit': cmd_edit,
        'scaffold': cmd_scaffold,
        'generate': cmd_model,
        'lsp': cmd_lsp,
        'help': lambda _: print(help_text()),
        '--help': lambda _: print(help_text()),
    }

    if cmd in subcommands:
        subcommands[cmd](cmd_args)
        return

    path = cmd
    if not os.path.exists(path):
        print(f"zap: unknown command or file not found: {path}", file=sys.stderr)
        print(help_text(), file=sys.stderr)
        sys.exit(1)

    try:
        result = run_file(path)
        if result is not None:
            print(result)
    except Exception as e:
        print(f"zap: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
