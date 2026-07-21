import sys, os, traceback
from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator

errors = []
for f in sorted(os.listdir('examples')):
    if not f.endswith('.zap'):
        continue
    path = os.path.join('examples', f)
    src = open(path).read()
    try:
        l = Lexer(src, f)
        tokens = l.tokenize()
        p = Parser(tokens)
        prog = p.parse()
        ok = (len(prog.stmts) > 0)
    except Exception as e:
        errors.append(f'{f}: parse error: {e}')
        traceback.print_exc()
        continue

    try:
        ev = Evaluator()
        for i, stmt in enumerate(prog.stmts):
            ev._eval_stmt(stmt)
        print(f'PASS: {f} ({len(prog.stmts)} stmts)', file=sys.stderr)
    except Exception as e:
        errors.append(f'{f}: eval error at stmt {i}: {e}')
        traceback.print_exc()

if errors:
    for e in errors:
        print(f'FAIL: {e}', file=sys.stderr)
    sys.exit(1)
else:
    print(f'All examples passed.', file=sys.stderr)
