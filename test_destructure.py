import sys
sys.path.insert(0, '.')
from src.evaluator import Evaluator
from src.parser import Parser
from src.lexer import Lexer

src = 'let {a, b} = ["a": 1, "b": 2]\nprint(a)\nprint(b)\n'
tokens = Lexer(src, '<test>').tokenize()
ast = Parser(tokens).parse()
result = Evaluator().eval(ast)
print('Result:', result)
