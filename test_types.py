import sys, os
from src.lexer import Lexer
from src.parser import Parser
from src.types import TypeChecker, INT, FLOAT, STR, BOOL, NONE, ANY, ListType, FunctionType

# Test 1: Basic inference
src = """
let x = 42
let y = "hello"
let z: float = 3.14
let b = True
"""
l = Lexer(src, 'test')
tokens = l.tokenize()
p = Parser(tokens)
prog = p.parse()
tc = TypeChecker()
tc.check(prog)
print(f"Test 1 - Basic inference: {len(tc.errors)} errors", file=sys.stderr)
for e in tc.errors:
    print(f"  {e}", file=sys.stderr)
assert len(tc.errors) == 0, f"Expected 0 errors, got {len(tc.errors)}"

# Check types
assert tc.env.get('x')[0] == INT
assert tc.env.get('y')[0] == STR
assert tc.env.get('z')[0] == FLOAT
assert tc.env.get('b')[0] == BOOL
print("  All type assertions passed", file=sys.stderr)

# Test 2: Type error
src2 = """
let x: int = "hello"
"""
l2 = Lexer(src2, 'test')
tokens2 = l2.tokenize()
p2 = Parser(tokens2)
prog2 = p2.parse()
tc2 = TypeChecker()
tc2.check(prog2)
print(f"Test 2 - Type mismatch: {len(tc2.errors)} errors (expected 1)", file=sys.stderr)
assert len(tc2.errors) == 1, f"Expected 1 error, got {len(tc2.errors)}"
assert 'int' in tc2.errors[0][2] and 'str' in tc2.errors[0][2]
print("  Correct error detected", file=sys.stderr)

# Test 3: Function calls
src3 = """
fn add(a: int, b: int) -> int:
  ret a + b

let result = add(1, 2)
say(result)
"""
l3 = Lexer(src3, 'test')
tokens3 = l3.tokenize()
p3 = Parser(tokens3)
prog3 = p3.parse()
tc3 = TypeChecker()
tc3.check(prog3)
print(f"Test 3 - Function typing: {len(tc3.errors)} errors", file=sys.stderr)
for e in tc3.errors:
    print(f"  {e}", file=sys.stderr)
assert len(tc3.errors) == 0, f"Expected 0 errors, got {len(tc3.errors)}"

# Test 4: Wrong args
src4 = """
fn add(a: int, b: int) -> int:
  ret a + b

add("hello", 2)
"""
l4 = Lexer(src4, 'test')
tokens4 = l4.tokenize()
p4 = Parser(tokens4)
prog4 = p4.parse()
tc4 = TypeChecker()
tc4.check(prog4)
print(f"Test 4 - Wrong arg types: {len(tc4.errors)} errors (expected 1)", file=sys.stderr)
assert len(tc4.errors) >= 1, f"Expected >=1 error, got {len(tc4.errors)}"

# Test 5: List typing
src5 = """
let nums = [1, 2, 3]
let first = nums[0]
"""
l5 = Lexer(src5, 'test')
tokens5 = l5.tokenize()
p5 = Parser(tokens5)
prog5 = p5.parse()
tc5 = TypeChecker()
tc5.check(prog5)
print(f"Test 5 - List typing: {len(tc5.errors)} errors", file=sys.stderr)
assert len(tc5.errors) == 0
assert tc5.env.get('nums')[0] == ListType(INT)
assert tc5.env.get('first')[0] == INT

# Test 6: Return type mismatch
src6 = """
fn bad() -> int:
  ret "hello"
"""
l6 = Lexer(src6, 'test')
tokens6 = l6.tokenize()
p6 = Parser(tokens6)
prog6 = p6.parse()
tc6 = TypeChecker()
tc6.check(prog6)
print(f"Test 6 - Return type mismatch: {len(tc6.errors)} errors (expected 1)", file=sys.stderr)
assert len(tc6.errors) >= 1, f"Expected >=1 error, got {len(tc6.errors)}"

print("\nAll type system tests passed!", file=sys.stderr)
