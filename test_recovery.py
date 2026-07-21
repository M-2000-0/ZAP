import sys
from src.lexer import Lexer
from src.parser import Parser

# Test error recovery with a syntax error mid-file
src = """
fn good():
  ret 1

let x = = 42

fn also_good():
  ret 2
"""
l = Lexer(src, 'test')
tokens = l.tokenize()
p = Parser(tokens)
p.recovery_mode = True  # Enable recovery
prog = p.parse()
print(f"Errors: {len(p.errors)}", file=sys.stderr)
for e in p.errors:
    print(f"  {e}", file=sys.stderr)
print(f"Statements: {len(prog.stmts)}", file=sys.stderr)
for i, s in enumerate(prog.stmts):
    print(f"  [{i}] {type(s).__name__}", file=sys.stderr)
assert len(prog.stmts) >= 2, f"Expected at least 2 stmts, got {len(prog.stmts)}"

# Test recovery in a block
src2 = """
fn test():
  let a = 1
  bad syntax here
  let b = 2
  ret b
"""
l2 = Lexer(src2, 'test')
tokens2 = l2.tokenize()
p2 = Parser(tokens2)
p2.recovery_mode = True
prog2 = p2.parse()
print(f"\nBlock recovery:", file=sys.stderr)
print(f"Errors: {len(p2.errors)}", file=sys.stderr)
for e in p2.errors:
    print(f"  {e}", file=sys.stderr)
print(f"Statements: {len(prog2.stmts)}", file=sys.stderr)
for i, s in enumerate(prog2.stmts):
    print(f"  [{i}] {type(s).__name__}", file=sys.stderr)

print("\nRecovery tests passed!", file=sys.stderr)
