from src.lexer import Lexer
from src.parser import Parser

src = """service Test
  version "1.0.0"
  requires:
    auth
  guarantees:
    atomic
  fn handle()
    ret "ok"
"""
l = Lexer(src, 'test')
tokens = l.tokenize()
for t in tokens:
    print(t)
print('---')
try:
    p = Parser(tokens)
    prog = p.parse()
    print('Parsed OK')
except SyntaxError as e:
    print('Parse error:', e)
