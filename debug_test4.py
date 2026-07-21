from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator
import sys

src = """
say("before concurrent")
concurrent:
  say("branch a")
  say("branch b")
say("after concurrent")
"""

l = Lexer(src, 'test')
tokens = l.tokenize()
p = Parser(tokens)
prog = p.parse()
print(f"Parsed: {len(prog.stmts)} stmts", file=sys.stderr)
ev = Evaluator()
ev.evaluate(prog)
print("Done", file=sys.stderr)
