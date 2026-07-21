from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator

src = """
say("before service")

service Simple:
  version "1.0.0"
  requires:
    logged_in
  guarantees:
    atomic
  expose do_stuff
  fn do_stuff()
    ret "done"

say("after service")
let svc = Simple
say("name:", svc.__name__)
say("version:", svc.__version__)
"""

l = Lexer(src, 'test')
tokens = l.tokenize()
# for t in tokens:
#     print(t)
try:
    p = Parser(tokens)
    prog = p.parse()
    print("Parsed OK, stmts:", len(prog.stmts))
    ev = Evaluator()
    ev.evaluate(prog)
    print("Evaluated OK")
except Exception as e:
    import traceback
    traceback.print_exc()
