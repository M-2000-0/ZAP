# Auto-generated Zap wrapper for examples/hello.zap
from __future__ import annotations
import json
from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator

zap_source = "print(\"hello from zap!\")\nprint(\"the future of AI coding\")\n"
filepath = "examples/hello.zap"

tokens = Lexer(zap_source, filepath).tokenize()
prog = Parser(tokens).parse()
ev = Evaluator(current_file=filepath)
result = ev.evaluate(prog)
if result is not None:
    print(result)
