import sys, os, traceback
from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator

errors = []
for f in ('beginners.zap', 'nextgen.zap', 'ai_native.zap'):
    path = os.path.join('examples', f)
    src = open(path).read()
    try:
        l = Lexer(src, f)
        tokens = l.tokenize()
        p = Parser(tokens)
        prog = p.parse()
        print(f'{f}: parsed {len(prog.stmts)} stmts, pos {p.pos}/{len(tokens)}', file=sys.stderr)
    except Exception as e:
        errors.append(f'{f}: parse error: {e}')
        traceback.print_exc()
        continue
    
    try:
        ev = Evaluator()
        for i, stmt in enumerate(prog.stmts):
            ev._eval_stmt(stmt)
        print(f'{f}: evaluated OK', file=sys.stderr)
    except Exception as e:
        errors.append(f'{f}: eval error at stmt {i}: {e}')
        traceback.print_exc()

for e in errors:
    print(f'FAIL: {e}', file=sys.stderr)
