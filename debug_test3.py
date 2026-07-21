import sys
from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator

src = open('examples/ai_native.zap').read()

l = Lexer(src, 'ai_native.zap')
tokens = l.tokenize()
print(f"Tokens: {len(tokens)}")
try:
    p = Parser(tokens)
    prog = p.parse()
    print(f"Parsed OK: {len(prog.stmts)} stmts")
    ev = Evaluator()
    try:
        for i, stmt in enumerate(prog.stmts):
            print(f"[debug stmt {i}] {type(stmt).__name__}", file=sys.stderr)
            ev._eval_stmt(stmt)
        print("Evaluated OK (no error)", file=sys.stderr)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR on stmt {i}: {e}", file=sys.stderr)
except SyntaxError as e:
    print(f"SyntaxError: {e}")
except Exception as e:
    import traceback
    traceback.print_exc()
