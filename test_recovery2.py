import sys
from src.lexer import Lexer
from src.parser import Parser

# Test recovery with actual syntax errors
src = """
fn good():
  ret 1

fn bad(a b c):

fn also_good():
  ret 2
"""
l = Lexer(src, 'test')
tokens = l.tokenize()
p = Parser(tokens)
try:
    prog = p.parse()
    print("Normal mode (should fail): parsed OK")
except SyntaxError as e:
    print(f"Normal mode correctly failed: {e}", file=sys.stderr)

# Recovery mode
p2 = Parser(tokens)
p2.recovery_mode = True
prog2 = p2.parse()
print(f"Recovery mode: {len(p2.errors)} errors, {len(prog2.stmts)} stmts", file=sys.stderr)
for i, e in enumerate(p2.errors):
    print(f"  Error {i}: {e}", file=sys.stderr)
assert len(prog2.stmts) >= 2, f"Expected at least 2 stmts (before & after error), got {len(prog2.stmts)}"

# Test recovery in fn body
src2 = """
fn test():
  let a = 1
  if a > 
    ret a
  ret 0
"""
l2 = Lexer(src2, 'test')
tokens2 = l2.tokenize()
p3 = Parser(tokens2)
p3.recovery_mode = True
prog3 = p3.parse()
print(f"\nFn body recovery: {len(p3.errors)} errors, {len(prog3.stmts)} stmts", file=sys.stderr)
for i, e in enumerate(p3.errors):
    print(f"  Error {i}: {e}", file=sys.stderr)

print("\nRecovery tests passed!", file=sys.stderr)
