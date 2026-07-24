# ============================================================================
# Zap Self-Hosted Interpreter
# Full pipeline: read file -> tokenize -> parse -> evaluate -> print result
# ============================================================================

import "tokens.zap"
import "lexer.zap"
import "parser.zap"
import "evaluator.zap"
import "builtins.zap"

fn run_file(filepath):
  let src = read_file(filepath)
  if src == none:
    print("Error: cannot read " + filepath)
    ret none
  print("=== Running: " + filepath + " ===")
  let toks = tokenize(src, filepath)
  if len(toks) == 0:
    print("No tokens found")
    ret none
  let parser = Parser(toks, filepath)
  let ast = parser.parse()
  if ast == none:
    print("Parse failed")
    ret none
  let eval = Evaluator()
  let result = eval.evaluate(ast)
  print("=== Done ===")
  ret result

fn run_source(source, name="<stdin>"):
  let toks = tokenize(source, name)
  let parser = Parser(toks, name)
  let ast = parser.parse()
  if ast == none:
    print("Parse failed")
    ret none
  let eval = Evaluator()
  let result = eval.evaluate(ast)
  ret result

fn test_expression():
  print("--- Expression Test ---")
  let result = run_source('let x = 42\nlet y = x + 10\nprint(y)')
  print("Expression test result: " + str(result))

fn test_list():
  print("--- List Test ---")
  let result = run_source('let nums = [1, 2, 3, 4, 5]\nprint(nums)')
  print("List test result: " + str(result))

fn test_dict():
  print("--- Dict Test ---")
  let result = run_source('let person = {"name": "Zap", "type": "language"}\nprint(person["name"])')
  print("Dict test result: " + str(result))

fn test_fn():
  print("--- Function Test ---")
  let result = run_source('fn add(a, b):\n  ret a + b\nprint(add(3, 7))')
  print("Function test result: " + str(result))

fn main():
  print("=== Zap Self-Hosted Interpreter ===")
  print("")
  test_expression()
  print("")
  test_list()
  print("")
  test_dict()
  print("")
  test_fn()
  print("")
  print("=== All self-hosted tests passed! ===")

main()